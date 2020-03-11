#@UnresolvedImport
#@UnusedVariable
#  modsel-retrosheet.py - Performs linear regression analysis on baseball data.
#     Copyright (C) 2020  Geoffrey G. Messier
# 
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
# 
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
import numpy as np;
import matplotlib.pyplot as plt;
import math, copy, random;
import pymysql.cursors;
import re;
import datetime as dt;
import pickle;
import random;
import operator as op
import time;
import copy;

import linreg as LinRegression;

cvFrac = 0.3;
nRandDataPicks = 5;
numTrainVals = 5;

xAttr = np.load('x-retrosheet.npz')['x'];
y = np.load('y-retrosheet.npz')['y'];

#xAttr = np.array([ [ 2, 3 ], [ 2, 3 ], [2, 3] ]);
#y = np.array([1,2,3]);
#xAttr = np.ones(3)*2;
    
mAttr = xAttr.shape[0];
mCv = int(mAttr*cvFrac);
mTrainMax = int(mAttr*(1.0 - cvFrac));
expY = np.mean(y);

mTrainVals = [ mAttr ];
for ind in range(0,numTrainVals):
    mTrainVals = [ int(mTrainVals[0]/2) ] + mTrainVals;
    
print("Training Vals: ",mTrainVals);

lrHyp = LinRegression.Hypothesis(
    convrgThresh = 0.05, poly=2, lam=0);

lrHyp.LoadTrainData(xAttr, y);


jCv = np.zeros(len(mTrainVals));
jTrain = np.zeros(len(mTrainVals));

for im in range(0,len(mTrainVals)):
    
    mTrain = int( min([mTrainVals[im], mTrainMax ]) );
    mTrainVals[im] = mTrain;
    
    print('-- mTrain: ',mTrain,' --');

    for iPick in range(0,nRandDataPicks):
        
        #print('Pick: ',iPick);
    
        inds = random.sample(range(0,mAttr),mTrain+mCv);

        lrHyp.Train(inds[0:mTrain]);
    
        jTrain[im] += lrHyp.SqError(inds[0:mTrain]);
        jCv[im] += lrHyp.SqError(inds[mTrain:-1]);
    
    jCv[im] /= nRandDataPicks;
    jTrain[im] /= nRandDataPicks;

    print('jTrain: ',jTrain[im],', jCv: ',jCv[im],', Pct Diff: ',abs(jTrain[im]-jCv[im])/jCv[im]*100,", Exp{y}: ",expY);


plt.loglog(mTrainVals,jTrain,'r');
plt.loglog(mTrainVals,jCv,'b');
plt.show();

'''
plt.plot(xAttr,y,'go');
plt.plot(xAttr,lrHyp.Predict(range(0,mAttr)),'ko');
plt.show();
'''














