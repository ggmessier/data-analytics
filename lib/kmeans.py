# Class for performing k-means clustering on multi-dimensional data.

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.special as scisp
import scipy.stats as scist


import warnings
warnings.filterwarnings("ignore")

class KMeansCluster:
    
    # Class constructor.
    def __init__(self,k,tbl):
        self.k = k
        self.nDat = len(tbl.index)   # Number of data points.
        self.nDim = len(tbl.columns)  # Number of dimensions in the data.
        
        self.tbl = tbl  # Store a reference to the original data.

        # Store a copy of the data that will be altered by normalization.
        self.dat = self.tbl.copy()  

        # Temporary storage for the squared distance from each data point to each cluster centroid.
#        self.tmpDists2 = np.zeros((self.nDat,k))  
        self.tmpDists2 = pd.DataFrame([ [0.0] * self.k for _ in range(self.nDat) ], index = self.tbl.index)
        
        # Cluster information. 
        self.clstr = pd.DataFrame({ 
            'id': [0]*self.nDat,      # Which cluster a data point belongs to.
            'dist2': [0.0]*self.nDat  # Squared distance of a data point to its cluster centroid.
            }, index = self.tbl.index )
        
        self.mus = np.zeros((k,self.nDim))  # Storage for the centroids of each cluster.
        self.musPrev = self.mus.copy()               # Storage for centroids of previous cluster iteration.
        
        # Perform z-standardization on the data (normalize to zero mean and unit variance)
        self.dat = (self.dat - self.dat.mean(axis=0))/np.sqrt(self.dat.var(axis=0))
        
        # Initialize the clusters
        self.InitClusters()
     
     
    # Initializes cluster membership before first iteration.   
    def InitClusters(self):
        
        # Perform random cluster initialization where each data point is randomly assigned cluster membership.
        self.clstr.id = pd.Series(np.random.randint(self.k, size=self.nDat),index = self.tbl.index)
        
        # Determine the resulting centroids.
        for ik in range(self.k):
            self.mus[ik,:] = self.dat.loc[self.clstr.id == ik,:].mean(axis=0)   

        
    # Performs a single cluster reassignment iteration.    
    def Update(self):
        
        # Store the previous centroid values.
        self.musPrev = self.mus.copy()

        # Determine the squared distances from each data point to each cluster centroid.
        for ik in range(self.k):
            self.tmpDists2.loc[:,ik] = ((self.dat - self.mus[ik,:])**2).sum(axis=1)
        
        # Assign data points to the closest cluster centroid.
        self.clstr['id'] = self.tmpDists2.idxmin(axis=1)  
        
        # Record the square distances of each data point to their cluster centroids.  
        self.clstr['dist2'] = self.tmpDists2.min(axis=1)   
        
        # Update the cluster centroids based on the reassigned data.
        for ik in range(self.k):
            self.mus[ik,:] = self.dat.loc[self.clstr.id == ik,:].mean(axis=0)   
    
        # Determine the within point scatter
        self.scatter = self.clstr.dist2.sum()
        
    
    # Finds the final cluster assignments. 
    # - The algorithm runs nInits times.  
    # - Each time, algorithm reinitializes with random cluster assignments and runs till the percent change
    #   in within point scatter is less than cnvrgPct.
    # - Out of the nInits cluster assignments calculated, the cluster assignment with the minimum spread is returned. 
    def Solve(self,nInits,cnvrgPct):
        
        # Variables to keep track of the best cluster assignment 
        minScatter = 1e300
        minMus = self.mus.copy()
        self.minClusters = self.clstr.copy()
                
        for _ in range(nInits):
            scatterPrev = 1e300
            self.scatter = 0.5e300
            
            self.InitClusters()
            
            while abs((self.scatter-scatterPrev)/scatterPrev) > cnvrgPct:                
                scatterPrev = self.scatter
                self.Update()
        
        if self.scatter < minScatter:
            minScatter = self.scatter
            minMus = self.mus.copy()
            self.minClusters = self.clstr.copy()
        
        # We return the centroid values re-calculated for the non-normalized data using the final cluster assignments.
        self.finalMus = np.zeros((self.k,self.nDim))
        for ik in range(self.k):
            self.finalMus[ik,:] = self.tbl.loc[self.minClusters.id == ik,:].mean(axis=0)   
                    
        return (self.finalMus,self.minClusters.id,self.CalcPValues(minMus, self.minClusters))
    
    
    
    # Uses Hotelling's test to determine if the differences between cluster centroids
    # are statistically significant.
    # Reference: https://en.wikipedia.org/wiki/Hotelling%27s_T-squared_distribution#Two-sample_statistic
    def CalcPValues(self,mus,clstr):
        
        nComp = scisp.comb(self.k,2,exact=True)  # Number of comparisons between centroids.
        pTable = pd.DataFrame({ 
            'i': [0]*nComp, 'j': [0]*nComp,  # Indices to represent the centroids being compared.
            'pVal': [0]*nComp                # p-value indicating statistical significance.
            })
                
        pInd = 0
        p = self.nDim
        for i in range(self.k):
            for j in range(i+1,self.k):
                
                # Number of data samples in cluster groups i and j.
                iN = sum(clstr.id==i) 
                jN = sum(clstr.id==j)
                                
                # Covariance matrices of the data in the two cluster groups.
                iCov = np.cov(self.dat.loc[clstr.id==i,:],rowvar=False)
                jCov = np.cov(self.dat.loc[clstr.id==j,:],rowvar=False)
                
                # Inverse of the pooled covariance matrix estimate
                invCov = np.linalg.inv( ((iN-1)*iCov+(jN-1)*jCov)/(iN+jN-1) )
        
                # Hotelling's two sample test statistic (analagous to the difference between two normalized means in the t-test).
                t2Val = iN*jN/(iN+jN) * (mus[i,:]-mus[j,:]).T @ invCov @ (mus[i,:]-mus[j,:])
                
                # Hotelling's distribution can be approximated by the f-distribution if scaled as follows.
                # - Important since scipy has a CDF for the f-distribution but not one for the Hotelling's distribution.
                fVal = t2Val * (iN+jN-p-1)/((iN+jN-2)*p)
          
                pTable.loc[pInd,'i'] = i
                pTable.loc[pInd,'j'] = j
                
                # Determine p-val (probability the difference between the two means was due to standard sampling error).
                pTable.loc[pInd,'pVal'] = 1-scist.f.cdf(fVal,p,iN+jN-1-p)  

                pInd += 1
            
        return pTable
    
    # Visualization routine for the centroids and cluster groups.    
    def Visualize(self):   
        
        if self.nDim != 2:
            print('ERROR: KMeansCluster::Visualize() only works with 2D data.')
            return

        try:
            self.finalMus
        except NameError:
            print('ERROR: Need to call KMeansCluster::Solve() before KMeansCluster::Visualize()')
            return
        else:
            xColIdx = [ True, False ]
            yColIdx = [ False, True ]
        
            for ik in range(self.k):
                rowIdx = (self.minClusters.id == ik)     
                plt.plot(self.tbl.loc[rowIdx,xColIdx],self.tbl.loc[rowIdx,yColIdx],'o')

            plt.plot(self.finalMus[:,0],self.finalMus[:,1],'ko',markersize = 15)
            plt.show()
                
        
if __name__ == '__main__':
    
    nDat = 10000
    muOffset = 5

    # Two clearly separated Gaussian distributed datasets.
    # - An example of finding two actual clusters of data.
    tbl1 = pd.DataFrame({ 'x': np.random.randn(nDat), 'y': np.random.randn(nDat) })
    tbl1.iloc[::2] += muOffset

    clusters = KMeansCluster(2,tbl1)
    (clstrMus,clstrAsgn,pTable) = clusters.Solve(10,0.001)
    
    print('-- Gaussian Example Data --')
    print('Centroids:')
    print(clstrMus)
    print('Hotelling\'s Test Results:')
    print(pTable)
    print('')
    clusters.Visualize()


    # A uniformly distributed dataset around a circular area.
    # - An example of finding the Voronoi tesselation for uniform data.
    tbl2 = pd.DataFrame({ 'x': np.random.rand(nDat), 'y': np.random.rand(nDat) })
    tbl2 = tbl2[ np.sqrt(tbl2.x**2 + tbl2.y**2) < 1]
    
    clusters = KMeansCluster(3,tbl2)
    (clstrMus,clstrAsgn,pTable) = clusters.Solve(10,0.001)
    
    print('-- Uniform Example Data --')
    print('Centroids:')
    print(clstrMus)
    print('Hotelling\'s Test Results:')
    print(pTable)
    print('')
    clusters.Visualize()

    
    # Verify the Hotelling's test routine by doing a p-value test for data that really is
    # different based only on sampling error.
    
    clusters.dat = pd.DataFrame({ 'x': np.random.randn(nDat), 'y': np.random.randn(nDat) })
    clusters.k  = 2
    randClstr = pd.DataFrame({ 'id': np.random.randint(2,size=nDat) }) # Randomly assign clusters.
    mus = np.array([ 
        list(clusters.dat.loc[randClstr.id == 0,:].mean(axis=0)),
        list(clusters.dat.loc[randClstr.id == 1,:].mean(axis=0))
        ])
    
    print('-- Hotelling\'s Test for Random Sampling Error Only --')
    print('Centroids:')
    print(mus)     
    print('Hotelling\'s Test Results:')
    print(clusters.CalcPValues(mus, randClstr))
    print('Typically we reject any p-value larger than 0.05.')
    
    
    
    
