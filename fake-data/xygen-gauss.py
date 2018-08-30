#@UnresolvedImport
#@UnusedVariable
import numpy as np;
import matplotlib.pyplot as plt;
import math, copy, random;
import pymysql.cursors;
import re;
import datetime as dt;
import pickle;
import random;


nPoints = 200;
xMax = 10;

xEqn = np.arange(0,xMax,xMax/nPoints);
yEqn = 2 + xEqn*4 - (0.3*xEqn)**3;

x = xEqn + np.random.normal(size=(nPoints))*xMax/nPoints/3;
y = yEqn + np.random.normal(size=(nPoints))*2;

plt.plot(x[0:-1:2],y[0:-1:2],'ro');
plt.show();


        
np.savez_compressed('x-gauss',x=x);
np.savez_compressed('y-gauss',y=y);










