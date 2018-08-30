#@UnresolvedImport
#@UnusedVariable
import numpy as np;
import math, copy, random;
import time;


# See if we can make this as generic as possible. 
# - The different algorithm modules will all have a class called Hypothesis since we need to use dot notation anyway.
# - Try to keep all algorithm specific parameters as c'tor arguments.
# - All algorithms will need to:
#  > Load training data (to make sure they do any algorithm specific mapping only once)
#  > Train on particular indices.  
#  > Once trained, determine random squared error on other indices.

class Hypothesis:
    
    def __init__(self, convrgThresh, poly=1, lam=0):
        self.convrgThresh = convrgThresh;
        self.poly = poly;
        self.lam = lam;
        


    def LoadTrainData(self, xAttr, y):
                
        if len(xAttr.shape) == 1:
            self.nAttr = 1;
        else:
            self.nAttr = xAttr.shape[1];

        self.mAttr = xAttr.shape[0];

        self.x = np.zeros((self.mAttr,1+self.nAttr*self.poly));
        self.x[:,0] = 1;
        
        for iPoly in range(1,self.poly+1):
            if self.nAttr == 1:
                self.x[:,iPoly] = xAttr**iPoly;
            else:
                self.x[:,(iPoly-1)*self.nAttr+1:iPoly*self.nAttr+1] = xAttr**iPoly;
                
        self.y = y;

     
    def Train(self, inds):
        m = len(inds);
        self.theta = np.zeros(1+self.nAttr*self.poly);
        hess = np.zeros((1+self.nAttr*self.poly,1+self.nAttr*self.poly));
        
        #print(' Training (Newton\'s Method):');

        sqErr = 1e300;
        sqErrPrev = 1e200;
        while(abs(sqErr-sqErrPrev) > self.convrgThresh ):

            sqErrPrev = sqErr;

            drvJs = np.zeros(1+self.nAttr*self.poly);
            
            sqErr = 0;    
            for ind in inds:
            
                for j in range(0,1+self.nAttr*self.poly):
                    drvJs[j] +=  1.0/m * (self.theta@self.x[ind,:] - self.y[ind])*self.x[ind,j] ;

                    for l in range(j,1+self.nAttr*self.poly):
                        hess[j,l] += 1.0/m * self.x[ind,j] * self.x[ind,l];
                    
                sqErr += (self.y[ind] - self.theta@self.x[ind,:])**2;

            for i in range(0,1+self.nAttr*self.poly):
                
                if i > 0:
                    drvJs[i] += self.lam/self.nAttr * self.theta[j];
                    hess[i,i] += self.lam;
                
                for j in range(0,i):
                    hess[i,j] = hess[j,i];


            self.theta -= np.linalg.pinv(hess) @ drvJs;

            sqErr /= m; 
        
            #print("   NrmSqErr: ",sqErr);
            #time.sleep(0.5);

        #print(' Final theta:', self.theta);
    
    
    def SqError(self, inds):
        m = len(inds);
        sqErr = 0;
        for ind in inds:
            sqErr += (self.y[ind] - self.theta@self.x[ind,:])**2;
        return sqErr/m;
    
    def Predict(self, inds):
        vals = np.zeros(len(inds));
        iVal = 0;
        for ind in inds:
            vals[iVal] += self.theta @ self.x[ind,:];
            iVal += 1;
        
        return vals;
    








