#@UnresolvedImport
#@UnusedVariable
#  xygen-retrosheet.py - Extracts data for machine learning testing from the Retrosheet baseball database.
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

# Credits a run for the player ID in runnerStr if the regex in scoreRegex would get him home.
def CreditRun(runnerStr, scoreRegex):
    if(len(runnerStr) > 0):
        runnerInd = plyrId2Ind[runnerStr];
        data[runnerInd,colR] += len(scoreRegex.findall(result[1]));


dataCols = {
    'AB': 0,
    'OBP': 1,
    'Slug': 2,
    'RBI': 3,
    'R': 4,
    'H': 5
    };

timeWin = 4; # Observation time window (weeks)

# True features are averaged over timeWin and presented as a single value.  False if vector of weekly values presented instead.
avgOverWin = True;  

# On base percentage (OBP)
#  <<H.*>> matches H,HR,H$,HR$,HP  
#  <<I.*>> matches I,IW

obpRegex = re.compile("^(W.*|S.*|D.*|T.*|DGR.*|E.*|FC.*|H.*|I.*)");
hitRegex = re.compile("^(S.*|D.*|T.*|DGR.*|H.*)"); # For now, includes being hit by a pitch.
singleRegex = re.compile("^S.*");
doubleRegex = re.compile("^D.*");
tripleRegex = re.compile("^T.*");
homerunRegex = re.compile("^H.*");
rbiRegex = re.compile("-H+");
base1ScoreRegex = re.compile(".*1-H.*");
base2ScoreRegex = re.compile(".*2-H.*");
base3ScoreRegex = re.compile(".*3-H.*");

# Some commented out so I don't have to work with multi-year data.
regSeasonStart = {
    2013 : dt.datetime(2013,3,31),
#    2014 : dt.datetime(2014,3,31),
#    2015 : dt.datetime(2015,4,5),
#    2016 : dt.datetime(2016,4,3),
#    2017 : dt.datetime(2017,4,2),
    };
    
regSeasonEnd = {
    2013 : dt.datetime(2013,10,30),
    2014 : dt.datetime(2014,10,29),
    2015 : dt.datetime(2015,11,1),
    2016 : dt.datetime(2016,10,2),
    2017 : dt.datetime(2017,11,1),
    };


players = {};
regSeasonWeeks = {};

# -- Determine Total Number of Weeks of Data --
totalWeeks = 0;
for key in regSeasonStart.keys():
    regSeasonWeeks[key] = int(np.ceil((regSeasonEnd[key]-regSeasonStart[key]).days/7));    
    totalWeeks += regSeasonWeeks[key];


# -- Conect to Database --
connection = pymysql.connect(host='127.0.0.1',
                         user='bbos',
                         password='bbos',
                         db='retrosheet',
                         cursorclass=pymysql.cursors.Cursor);
                             
cursor = connection.cursor();

# -- Find the Number of Distinct Players --
sqlString = "select distinct player_id, last_name_tx, first_name_tx from rosters;";

nFields = cursor.execute(sqlString);
print('Distinct Players: %d' % (nFields));

# Temporal data organization
# - x in R^{m \times n_Dat \cdot n_Time}
#    n_Dat : number of data features
#    n_Time : number of time points where we have n_Dat features
# - The time data for a particular stat is all lumped together.

data = np.zeros((nFields,len(dataCols)*totalWeeks));


# -- Create Player ID Data Structures --

# fields contains the retrosheet player ID and full player names
fields = [];

# plyrId2Ind translates the retrosheet player ID to the index storing that player's timeline
plyrId2Ind = {};

for ind in range(0,nFields):
    
    result = cursor.fetchone();
    fields.append({
        'ID' : result[0],
        'Last Name' : result[1],
        'First Name' : result[2]
        });
    plyrId2Ind[result[0]] = ind;


weekOffset = 0; # Offset used when storing multiple years of data
    
for key in regSeasonStart.keys():
    
    print("===== Year %d =====" % (key));
    
    gameDate = regSeasonStart[key];
    
    for iWkCurYear in range(0,regSeasonWeeks[key]):
        
        print(" --- Week %d/%d ---" % ( iWkCurYear, regSeasonWeeks[key] ));

        # Determine the column offsets used to store the different data fields.
        colObp = dataCols['OBP']*totalWeeks + weekOffset + iWkCurYear; 
        colAb = dataCols['AB']*totalWeeks + weekOffset + iWkCurYear; 
        colSlug = dataCols['Slug']*totalWeeks + weekOffset + iWkCurYear; 
        colRbi = dataCols['RBI']*totalWeeks + weekOffset + iWkCurYear;             
        colR = dataCols['R']*totalWeeks + weekOffset + iWkCurYear;            
        colHit = dataCols['H']*totalWeeks + weekOffset + iWkCurYear;             
    
        # This set records the number of players with valid data.  As set is used so each individual is counted only once.
        plyrVisited = set();
        
        # Check for a game each day of the week.
        for iDay in range(0,7):
            
            # Use a regex to find all games with ID's that match the current date.
            gameDate += dt.timedelta(days=1);
            gameDateField = "%d%02d%02d" % (gameDate.year, gameDate.month, gameDate.day);
            sqlString = "select bat_id, event_tx, base1_run_id, base2_run_id, base3_run_id from events where game_id regexp '^[A-Z]{3}%s.';" % ( gameDateField );
            
            nEvents = cursor.execute(sqlString);
               
            print("   Date String: %s, No. Events on Date: %d" % (gameDateField, nEvents));    
               
            # Go through all the events for all the games that came up for the current date.              
            for iEvent in range(0,nEvents):
                
                result = cursor.fetchone();
                plyrInd = plyrId2Ind[result[0]];  # Determine the data array index for the player found.
                plyrVisited.update([ plyrInd ]);  # Make note that this player has valid data.
                
                # Update the player with all the events recorded in the eventID string.
                data[plyrInd,colAb] += 1;
                data[plyrInd,colObp] += len(obpRegex.findall(result[1]));
                data[plyrInd,colRbi] += len(rbiRegex.findall(result[1]));
                data[plyrInd,colHit] += len(hitRegex.findall(result[1]));
                data[plyrInd,colSlug] += len(singleRegex.findall(result[1]))*1;
                data[plyrInd,colSlug] += len(doubleRegex.findall(result[1]))*2;
                data[plyrInd,colSlug] += len(tripleRegex.findall(result[1]))*3;
                data[plyrInd,colSlug] += len(homerunRegex.findall(result[1]))*4;
                data[plyrInd,colR] += len(homerunRegex.findall(result[1]));
                
                # Use the base runner ID strings to see who scores a run off this hit.
                CreditRun(result[2],base1ScoreRegex);
                CreditRun(result[3],base2ScoreRegex);
                CreditRun(result[4],base3ScoreRegex);
        
        # Adjust all stats that are normalized by number of at bats.    
        for plyrInd in plyrVisited:
            if(data[plyrInd,colAb] > 0):
                data[plyrInd,colObp] /= data[plyrInd,colAb];
                data[plyrInd,colSlug] /= data[plyrInd,colAb];
    
    # Update by the number of weeks in the current season.
    weekOffset += regSeasonWeeks[key];
    

# Only consider active players (ones with at least one non-zero value in their timelines)
activeInds = np.argwhere(np.sum(data,axis=1));
nActive = len(activeInds[:,0]);

nWindows = totalWeeks - timeWin;  # Number of time windows we have in our timeline

if(avgOverWin):
    x = np.zeros((nActive*nWindows,len(dataCols)));
    n = len(dataCols);
else:
    x = np.zeros((nActive*nWindows,timeWin*len(dataCols)));
    n = timeWin*len(dataCols);

y = np.zeros((nActive*nWindows,1));
m = nActive*nWindows;

indTrain = 0;
for plyrInd in activeInds[:,0]:
    
    for indTime in range(timeWin,totalWeeks):

        for feature in dataCols.keys():
            datOffset = dataCols[feature]*totalWeeks + indTime;
            if(avgOverWin):
                xOffset = dataCols[feature];
                x[indTrain,xOffset] = np.sum(data[plyrInd,datOffset-timeWin:datOffset]);
            else:
                xOffset = dataCols[feature]*timeWin;
                x[indTrain,xOffset:xOffset+timeWin] = data[plyrInd,datOffset-timeWin:datOffset];
        
        hitOffset = dataCols['H']*totalWeeks + indTime;
        rbiOffset = dataCols['RBI']*totalWeeks + indTime;
        y[indTrain,0] = data[plyrInd,hitOffset] + data[plyrInd,rbiOffset];
        
        indTrain += 1;
        
np.savez_compressed('x-retrosheet',x=x);
np.savez_compressed('y-retrosheet',y=y);

print("Done! m: %d, n: %d" % (m,n));









