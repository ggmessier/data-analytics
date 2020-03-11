#@UnresolvedImport
#@UnusedVariable
#  xygen-gauss.py - Generates synthetic data for testing supervised learning routines.
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










