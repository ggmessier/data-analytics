#!/usr/bin/env python
# coding: utf-8

"""
Standard routines for pre-processing and analyzing client data from the Calgary Drop-In Centre.
Copyright (C) 2021 Geoffrey Guy Messier

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import pandas as pd
import numpy as np


# =========== Data Cleaning Routines ==============
def RemoveByStartDate(tbl,winStartDate,winEndDate,dateSelect = pd.Series(dtype='object')):
    """Remove all records for subjects in tbl first appearing in the data between
    winStartDate and winEndDate (determined using tbl.Date values)."""

    if dateSelect.empty:
        tblFlt = tbl
    else:
        tblFlt = tbl.loc[dateSelect]
        
    startDates = tblFlt.groupby('ClientId').apply(lambda x: min(x.Date))
    notCensored = ~ ((startDates >= winStartDate) & (startDates <= winEndDate ))
    
    return tbl.loc[tbl.ClientId.isin(startDates[notCensored].index)]    

# =========== Demographic Analysis =============
def ShelterGroupDemographics(tbl):
    """Summarizes the demographics of a group of shelter clients.
    - Fields:
     > TotalStays: Total number of shelter stays.
     > Tenure: Number of days between first and last appearance in dataset.
     > UsagePct: Percentage of days during tenure spent in shelter.
     > AvgGapLen: Average length of gaps between shelter stays (days).
                  NaN for clients with a single stay.
     > TotalEpisodes: Total number of episodes of shelter access.
     """
    
    # Generate a stay timeline
    dates = tbl.Date.drop_duplicates().sort_values() 
    tl = pd.DataFrame({
        'Date': dates,                
        'Ind': range(1,len(dates)+1)  
        })
    
    tenure = (tl.Date.max() - tl.Date.min()).days + 1
    gapVals = tl.Date.diff().astype('timedelta64[D]')
    nStays = tl.Ind.max()
    
    return pd.Series({
        'Tenure': tenure,  # Total span of days a client interacts with shelter.
        'UsagePct': 100.0*nStays/tenure,  # Percentage of days during tenure client stayed in shelter.
        'AvgGapLen': gapVals.mean(),  # Average length of gaps in shelter stays.
        'TotalStays': nStays,  # Total number of shelter stays.
        'TotalEpisodes': sum(gapVals >= episodeGap)+1  # Total number of episodes.
    })

# =========== Calculated Event Timeline Routines =============
def CalculateStaySequence(tbl):
    """Determines a stay timeline for a subject.
    - Each event in the timeline is represented by an index and a timestamp.
    - A stay is defined as accessing one or more services (typically sleep services) 
      in a 24 hour period.
    - Timestamps generated using tbl.Date values."""
    
    dates = tbl.Date.drop_duplicates().sort_values() # Drop duplicates since stay is one or more sleep.
    return pd.DataFrame({
        'Date': dates,                 # Date of each stay.
        'Ind': range(1,len(dates)+1)   # Index of each stay.
    })


episodeGap = 30  # The max gap in stays before a new episode is created.

def CalculateEpisodeSequence(tbl):    
    """Determines an episode timeline for a subject.  
    - Each event in the timeline is represented by an index and a timestamp.
    - An episode is a series of shelter stays separated by gaps of less than 
      di_data.episodeGap days.
    - A stay is defined as accessing one or more services (typically sleep services) 
      in a 24 hour period.
    - Timestamps generated using tbl.Date values."""
    
    stayDates = tbl.Date.drop_duplicates().sort_values() # Drop duplicates since stay is one or more sleep.
    gapVals = stayDates.diff().astype('timedelta64[D]')
    gapInd = (gapVals >= episodeGap).astype('int').cumsum().drop_duplicates(keep='first')
    
    return pd.DataFrame({
        'Date': tbl.loc[gapInd.index].Date, # Date of first day of each episode.
        'Ind': range(1,len(gapInd)+1)       # Episode index.
    })


def TimeWinThresholdTest(tbl,posFlag,negFlag,thresh,winSzDays):
    """Analyze a subject timeline and determine if the number of events
    are >= thresh in a time window of winSzDays.
    - idDate is the date the threshold test is satisfied.
    - reqTime is the number of days it took to satisfy the threshold test.
    - If the test is satisfied, return a series with posFlag, idDate and reqTime.
    - If the test is not satisfied, return a series with negFlag and nan values
      for idDate and reqTime."""
    
    # Apply a rolling time window of winSzDays.
    win = tbl.rolling('{:d}d'.format(winSzDays),on='Date').count().Ind
    
    registrationDate = tbl.Date.min()
    idDate = tbl[win >= thresh].Date.min()  # Will be equal to NaN if the threshold isn't met.
    reqTime = (idDate - registrationDate).days
    
    if idDate == idDate:   # Satisfied if idDate is not NaN.
        return pd.Series({
            'Flag': posFlag,  
            'Date': idDate,  # Date subject was identified.
            'Time': reqTime  # Number of days it took to identify subject.
        })
    else:
        return pd.Series({   # Returned if the test is not satisfied.
            'Flag': negFlag,
            'Date': pd.NaT,
            'Time': np.nan
        })

    
def ChooseEarliestTest(test1,test2):
    """Merges two test tables.  If each test is positive for a subject, the test that
    occurs earliest in a subject's timeline is chosen.  
    
    If you have more than two test tables, you can call this routine several times.  For 
    example, tables A, B and C can be merged by:
      mrg = ChooseEarliestTest(A,B)
      mrg = ChooseEarliestTest(mrg,C)
      
    Assumptions:
    - Both test tables contain the identical list of subjects.
    - Both tests use the same flag for a negative result.
    """
    nRec = len(test1.index)
    
    # Create a blank table where all clients are intially transient.  
    tbl = pd.DataFrame({ 'Flag': ['']*nRec, 'Date': [pd.NaT]*nRec, 'Time': [np.nan]*nRec },index=test1.index)

    # Populate the clients that are negative in both tables.
    bothNeg = (test1.Time != test1.Time) & (test2.Time != test2.Time)
    tbl[bothNeg] = test1[bothNeg]
    
    # Find all clients that are classified earliest or only by test 1.
    isOne = (test1.Time == test1.Time) & (test2.Time == test2.Time) & (test1.Time < test2.Time)
    isOne = isOne | ( (test1.Time == test1.Time) & (test2.Time != test2.Time) )
    tbl[isOne] = test1[isOne]
    
    # Find all clients that are classified earliest or only by test 2.
    isTwo = (test1.Time == test1.Time) & (test2.Time == test2.Time) & (test1.Time >= test2.Time)
    isTwo = isTwo | ( (test2.Time == test2.Time) & (test1.Time != test1.Time) )
    tbl[isTwo] = test2[isTwo]
    
    return tbl