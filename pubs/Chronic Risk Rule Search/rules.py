#!/usr/bin/env python
# coding: utf-8

"""This library provides routines for rule set searching.

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

import dask
from dask.distributed import Client
import sys
import numpy as np
import copy
from sklearn.model_selection import StratifiedKFold

import sys
sys.path.append('../util/')



# ------- Feature Generation -----------

def gen_coverage_table(attr,lbl):
    """Generates coverage table using the algorithm presented by Gamberger, et. al. in "Handling 
    unknown and imprecise attribute values in propositional rule learning: A feature-based approach".
    
    -- Parameters --
     attr: NxK attribute numpy array where N = number of examples and K = number of attributes.
     lbl: Nx1 numpy label vector where positive/negative examples are equal to 0/1.
     
    -- Returns --
     A 6-tuple consisting of the following:
      ftrStr: Array of human readable strings decribing feature tests (ie. "A0 <= 4.2").
      attrInds: Array of the attribute indices that correspond to each feature.
      vThrshs: Array of the threshold values used by each feature test.
      ops: Array of strings indicating the feature test operation (equal to '<', or '>=').
      covTbl: NxL numpy array where L is the number of features.
      labels: Nx1 numpy vector of label values.
    """
    exs = np.concatenate((attr,lbl),axis=1)
    attrCols = range(attr.shape[1])
    labelCol = attr.shape[1]
    print(' Number of Examples: {}'.format(len(lbl)))
    
    ftrStr = []  # Feature description strings.
    vThrshs = np.array([])  # Feature threshold values. 
    ops = []     # Feature test types (either < or >=).
    attrInds = []    # Attribute column indices used by each feature.
    
    # Determine features
    for attrCol in attrCols:
        
        # Extract and sort the unique attribute values.  These will form our decicion boundaries.
        srtVals = np.unique( exs[exs[:,attrCol].argsort()][:,[attrCol,labelCol]], axis=0)
        
        nFtrAdded = 0
        for i in range(srtVals.shape[0]-1):
                          
            # Calculate the midpoint between this attribute value and the next.
            vThrsh = (srtVals[i,0]+srtVals[i+1,0])/2

            # For a positive to negative label transition, create a < feature.
            if srtVals[i,1] == 1 and srtVals[i+1,1] == 0:                
                ftrStr.append('A{} < {:.3g}'.format(attrCol,vThrsh))
                vThrshs = np.append(vThrshs,vThrsh)
                ops.append('<')
                attrInds.append(attrCol)
                nFtrAdded += 1
              
            # For a negative to positive label transition, create a >= feature.
            if srtVals[i,1] == 0 and srtVals[i+1,1] == 1:
                ftrStr.append('A{} >= {:.3g}'.format(attrCol,vThrsh))
                vThrshs = np.append(vThrshs,vThrsh)
                ops.append('>=')
                attrInds.append(attrCol)
                nFtrAdded += 1
                
        print('  Attribute {} Features: {} ({} unique values)'.format(attrCol,nFtrAdded,srtVals.shape[0]))
                
         
    # Calculate coverage table
    covTbl = np.zeros((exs.shape[0],len(ftrStr)))
    for i in range(covTbl.shape[0]):
        for j in range(covTbl.shape[1]):
            if ops[j] == '<':
                covTbl[i,j] = exs[i,attrInds[j]] < vThrshs[j]
            else:
                covTbl[i,j] = exs[i,attrInds[j]] >= vThrshs[j]
    
    labels = exs[:,labelCol]
    
    return (ftrStr,attrInds,vThrshs,ops,covTbl,labels)


# ------- Feature Storage  -----------

class CoverageTableInfo:
    """
    Class for storing coverage table information.
    """
    
    def __init__(self, data):
        """Initialize member variables using coverage table dictionary.
        -- Parameters --
         data: Coverage table dictionary object generated by gen_coverage_table().
        """        
        self.AttrInds = np.array(data['AttributeIndices'])
        self.Operators = np.array(data['FeatureOperations'])
        self.ThreshVals = np.array(data['ThresholdValues'])
        self.FtrStrs = np.array(data['FeatureStrings'])
        
        self.nFtr = len(self.FtrStrs)
        
        
        
        
# ------- Rule Quality Routines -----------
        
class RuleQuality:
    """
    Rule quality base class that consolidates some common rule quality operations 
    and routines for evaluating rule performance.
    """
    
    def __init__(self, ftrStr):
        """Initialize member variables.
        -- Parameters --
         ftrStr: Array of feature strings from the Example class.
        """
        self.ftrStr = ftrStr
        self.head = np.array([],dtype=np.uint8)
        
        
    def size_head(self,headSize):
        """Resize the internal vector used to store the rule head calculation.
        -- Parameters --
         headSize: Desired vector size.
        """
        self.head = np.full(headSize,0,dtype=np.uint8)
        
        
    def get_head(self):
        """Returns the rule head vector.
        """
        return self.head
    
    
    def calc_head(self, rules, covTbl, labels):
        """Calculates a boolean array indicating which examples in the coverage table
        satisfy a rule set.
        -- Parameters --
         rules: 2D ruleset array containing feature index numbers.
         covTbl: numpy coverage table matrix.
         labels: numpy label vector.
        """
        
        # The head of the ruleset indicates the examples that test positive.
        self.head.fill(0)
        
        # Combine the rules in the rulesets disjunctively.
        for rule in rules:
            
            # Product is used since the individual features within a rule are
            # combined conjunctively.
            self.head += np.prod(covTbl[:,rule],axis=1,dtype=np.uint8)

        # Equivalent to the logical OR of the individual features selected by the rule.
        self.head = (self.head > 0).astype(np.uint8)
            

    
    def confusion_matrix(self, rules, covTbl, labels):
        """Returns a 2x2 numpy confusion matrix for a rule set.
        -- Parameters --
         rules: 2D ruleset array containing feature index numbers.
         covTbl: numpy coverage table matrix.
         labels: numpy label vector.
        """
        self.calc_head(rules, covTbl, labels)
        
        tPos = int( np.sum(self.head * labels) )
        fPos = int( np.sum(self.head * (1-labels)) )
        pos = int( np.sum(labels) )
        neg = len(labels) - pos
        fNeg = pos - tPos
        tNeg = neg - fPos

        return np.array([ [ tPos, fNeg ], [ fPos, tNeg ] ])  

    
    def ruleset_str(self, rules):
        """Generate a string containing a rule set in human readable (ish) format.
        -- Parameters --
         rules: 2D ruleset array containing feature index numbers.
        """
        
        rStr = ''
        for idx in range(len(rules)):
            rStr += '{}'.format(self.ftrStr[rules[idx]])
            if idx < len(rules)-1:
                rStr += '|'
        return rStr    
    
    
    def confusion_summary_str(self, cnf, idnt=''):
        """Returns a string summarizing the confusion matrix performance of a ruleset.
        -- Parameters --
         cnf: 2x2 confusion matrix.
         idnt: String of spaces used to indent output.
        """

        tPos = cnf[0,0]
        fNeg = cnf[0,1]
        fPos = cnf[1,0]
        tNeg = cnf[1,1]

        pos = tPos + fNeg
        neg = fPos + tNeg

        cnfStr = ''

        cnfStr += '{}Precision: {:.4f}\n'.format(idnt,tPos/max([1,(tPos+fPos)]))
        cnfStr += '{}Recall: {:.4f}\n'.format(idnt,tPos/pos)
        cnfStr += '{}Confusion:\n'.format(idnt)
        cnfStr += '{} True Pos: {}/{}\n'.format(idnt,tPos,pos)
        cnfStr += '{} False Neg: {}/{}\n'.format(idnt,fNeg,pos)
        cnfStr += '{} False Pos: {}/{}\n'.format(idnt,fPos,neg)
        cnfStr += '{} True Neg: {}/{}\n'.format(idnt,tNeg,neg)

        return cnfStr    
    

    def print_summary(self, rules, covTbl, labels):
        """Returns a string summarizing the overall performance of a ruleset.
        -- Parameters --
         rules: 2D ruleset array containing feature index numbers.
         covTbl: numpy coverage table matrix.
         labels: numpy label vector.
        """

        print('Rule: ',end='')
        print(self.ruleset_str(rules))
        print('')
        print(self.confusion_summary_str(self.confusion_matrix(rules,covTbl,labels),idnt=' '))
        
    
    def ruleset_coverage(self, rules, covTbl, labels, noFPos):
        """Returns the coverage of a ruleset broken into true and false positives.
        -- Parameters --
         rules: 2D ruleset array containing feature index numbers.
         covTbl: numpy coverage table matrix.
         labels: numpy label vector.
         noFPos: If true, set the returned false positive value to zero.  Used when
          OPUS needs to know the best rule performance possible by adding more 
          conjunctive features to that rule.
        """
        
        # Replicates the calculation from calc_head() to save a function call.
#        self.head.fill(0)
#        for rule in rules:
#            self.head += np.prod(covTbl[:,rule],axis=1,dtype=np.uint8)
#        self.head = (self.head > 0).astype(np.uint8)
                
        self.calc_head(rules, covTbl, labels)
        tPos = np.sum(self.head * labels, dtype=int)  # True positives.

        # Used when OPUS needs to know the best possible performance a single
        # rule consisting of conjunctive features.  This is determined by
        # setting the false positives to zero since adding more conjunctive 
        # features will, at best, eliminate all false positives and leave 
        # the true positives unchanged.
        if noFPos:
            fPos = 0
        else:
            fPos = np.sum(self.head * (1-labels), dtype=int) # False positives.


        return tPos, fPos
    

    
class RuleQualPrecision(RuleQuality):
    """Calculate precision/confidence for a rule set.
    """
    
    def __init__(self, ftrStr, minReqPosFrac=0):
        """Init member variables.
        -- Parameters --
         ftrStr: Coverage table feature string (from Examples).
         minReqPosFrac: Minimum fraction of positive cases the rule set must
          cover to return a positive value (0 <= minReqPosFrac <=1).
        """        
        super().__init__(ftrStr)
        
        # Set a minimum fraction of positive cases that the rule must
        # cover to return a nonzero value.  Prevents optimizing towards
        # rules with high precision but very small coverage.
        self.minReqPosFrac = minReqPosFrac
        
    
    def val(self, rules, covTbl, labels, noFPos=False):
        """Calculate quality metric.
        """
        
        tPos, fPos = self.ruleset_coverage(rules, covTbl, labels, noFPos)

        minReqPos = int(np.sum(labels)*self.minReqPosFrac)
        if tPos+fPos == 0 or tPos < minReqPos:
            return 0
        else:
            return tPos/(tPos+fPos)
        
        
        
class RuleQualFScore(RuleQuality):
    """Calculate f-score for a rule set.
    """
    
    def __init__(self, ftrStr, betaSq):
        """Init member variables.
        -- Parameters --
         ftrStr: Coverage table feature string (from Examples).
         betaSq: beta^2 value used in f-score calculation.         
        """        
        super().__init__(ftrStr)  
        
        self.betaSq = betaSq
        
    
    def val(self, rules, covTbl, labels, noFPos=False):
        """Calculate quality metric.
        """
                
        tPos, fPos = self.ruleset_coverage(rules, covTbl, labels, noFPos)

        if tPos + fPos > 0:
            precision = tPos/(tPos + fPos)
        else:
            precision = 0

        recall = tPos/np.sum(labels)

        if precision == 0 and recall == 0:
            return 0
        else:
            return (self.betaSq+1)*precision*recall/(self.betaSq*precision+recall)

        
class RuleQualRateDiff(RuleQuality):
    """Calculate true positive/false positive rate difference metric for rule set.
    """
    
    def __init__(self, ftrStr):
        """Init member variables.
        -- Parameters --
         ftrStr: Coverage table feature string (from Examples).
        """        
        super().__init__(ftrStr)
        

    def val(self, rules, covTbl, labels, noFPos=False):
        """Calculate quality metric.
        """
        
        tPos, fPos = self.ruleset_coverage(rules, covTbl, labels, noFPos)

        return tPos/np.sum(labels) - fPos/np.sum(1-labels)    
    
    
class RuleQualCoverageDiff(RuleQuality):
    """Calculate true positive/false positive coverage difference metric for rule set.
    """
    
    def __init__(self, ftrStr):
        """Init member variables.
        -- Parameters --
         ftrStr: Coverage table feature string (from Examples).
        """                
        super().__init__(ftrStr)

    
    def val(self, rules, covTbl, labels, noFPos=False):
        """Calculate quality metric.
        """
        
        tPos, fPos = self.ruleset_coverage(rules, covTbl, labels, noFPos)

        return tPos - fPos  
    
    
    
# ------- OPUS Rule Search -----------
    
OPUS_DEBUG_EXHAUSTIVE = 1
OPUS_DEBUG_RULE_DEPTH = 2

class OpusRuleSearch:
    """Implements the OPUS rule search algorithm.
    """
    
    def __init__(self, ruleQuality, maxRuleLen=None, debug=False):
        """Initializes member variables.
        
        -- Parameters --
         ruleQuality: Reference to the RuleQuality derived class object that calculates
          the rule metric used by OPUS to find the best rules.
         mxRuleLen: Maximum rule length.  Default (None) corresponds to the maximum 
          possible.
         debug: Debug level. Values:  
            rules.OPUS_DEBUG_EXHAUSTIVE generates exhaustive debug information suitable 
               for debugging very small example sets.
            rules.OPUS_DEBUG_RULE_DEPTH generates debug information upon finishing each
               level of the search tree.  Suitable for estimating the run time and rule
               length performance benefits for large example sets.
        """
        
        # Quality calculation used to evaluate rules (ie. precision, etc.).
        self.ruleQuality = ruleQuality 
        
        # Maximum rule length.
        self.maxRuleLen = maxRuleLen 
        
        # Attribute indices to search over.
        # - Note: One attribute will correspond to many features.
        self.searchAttr = None
        
        # Debug output.
        self.debug = debug
        self.debugUpdateFrac = 0.05
        
    
    def set_search_attributes(self, searchAttr): 
        """Set which attributes are included in the rule search.  Note that one attribute may
        correspond to many features.
        -- Parameters --
         searchAttr: Array of attribute index numbers (as defined in the Examples class).
        """
        self.searchAttr = searchAttr
        
        

    def find_rule(self, covTblInfo, covTbl, labels):
        """Perform the rule search.
        -- Parameters --
         covTblInfo: Coverage table feature information object.
         covTbl: Coverage table numpy array.
         labels: Coverage table numpy vector.
        """
        
        # Resize rule quality head vector.
        self.ruleQuality.size_head(len(labels))
        
        # If no max rule length is set, it's equal to the number of features.
        if self.maxRuleLen is None:
            self.maxRuleLen = covTblInfo.nFtr
        
        # Search all features if no specific attributes are selected.
        if self.searchAttr is None:
            searchFeatures = np.array(list( range( covTblInfo.nFtr ) ),dtype=np.ushort)
            
        # If attributes have been selected, only search over their features.
        else:
            searchFeatures = np.array(
                [ i for i in range(covTblInfo.nFtr) if np.isin(covTblInfo.AttrInds[i],self.searchAttr) ],
                dtype=np.ushort)
            
        nFtr = len(searchFeatures)
                
        # Initialize with the universal rule.
        # - A rule is a list of feature index numbers (universal rule is an empty list).
        # - A rule set is a 2D list where each element list contains a different rule.
        rules = [ [] ] 
        
        
        # Each rule (node) is assigned a set of features used to create its children in the tree.
        # These are stored as an array of feature indices.  The initial rule is assigned all features.
        asgnFeatures = [ searchFeatures ]

        # The best rule found so far defaults to the initial rule.
        bestRule = []
        bestQual = self.ruleQuality.val([ bestRule ],covTbl,labels)
        mxPotQual = [ self.ruleQuality.val([ bestRule ],covTbl,labels,noFPos=True) ]
        
        if self.debug == OPUS_DEBUG_RULE_DEPTH:
            curDepth = 1
        
        # Each interation through this loop expands the children of one rule in the rules list.
        rIdx = 0  # Index of the current node/rule being expanded.
        while(1):

                
            if self.debug == OPUS_DEBUG_RULE_DEPTH:
                if rIdx < len(rules): 
                    depthToDo = min([ len(i) for i in rules[rIdx:] ])
                else:
                    depthToDo = curDepth+1
                    
                if depthToDo > curDepth:
                    toDoMean = np.mean(mxPotQual[rIdx:]) if len(mxPotQual[rIdx:]) > 0 else np.nan
                    print(f'Finished Depth: {curDepth}')
                    print(f' MaxPotQuality: {np.mean(mxPotQual[:rIdx]):.2f} (evaluated), {toDoMean:.2f} (todo)')
                    print(f' Best Rule: {bestRule}:({self.ruleQuality.ruleset_str([bestRule])}), Quality: {bestQual}')
                    curDepth = depthToDo
            
            
            if self.debug == OPUS_DEBUG_EXHAUSTIVE:
                print('---------------------------------------\nRules: ',end='')
                for r in rules:
                    print(f'{r}:({self.ruleQuality.ruleset_str([r])}), ',end='')
                print(f'\nFeatures Assigned to Rules: {asgnFeatures}')
                print(f'Rule Max Potential Quality: {mxPotQual}')
                
            # Terminate if we've finished expanding all the rules in our list.
            if rIdx == len(rules):
                break
                
            # Otherwise, the next rule in the list becomes the current rule to be expanded.
            else:
                rCur = rules[rIdx]
                
                # The features assigned to this node will be used to create its children.
                childFeatures = copy.copy(asgnFeatures[rIdx])

            # Only add features to this rule if the result will be <= the max length.
            if len(rCur)+1 > self.maxRuleLen:
                rIdx += 1
                continue
                
            # Create new rules by conjunctively adding new features to rCur.
            newRules = []
            newRuleMxPotQual = []
            for ftr in childFeatures:

                rNew = rCur + [ ftr ]
                newRules += [ rNew ]
                newRuleMxPotQual += [ self.ruleQuality.val([ rNew ],covTbl,labels,noFPos=True) ]

                # Check if we've found a new best rule.
                if self.ruleQuality.val([ rNew ],covTbl,labels) > bestQual:
                    bestRule = rNew
                    bestQual = self.ruleQuality.val([ bestRule ],covTbl,labels)
                    
                    if self.debug == OPUS_DEBUG_EXHAUSTIVE:
                        print(f' New Best! {bestRule} (Qual: {bestQual})')

                    # Prune any existing rules with max potential qualities lower
                    # then the actual quality of the new rule.
                    nRules = len(rules)
                    idx = 0
                    while idx < nRules:
                        if mxPotQual[idx] < bestQual:
                            
                            if self.debug == OPUS_DEBUG_EXHAUSTIVE:
                                print(f' Best rule prunes: {rules[idx]} (MxPotQual: {mxPotQual[idx]}, Features: {asgnFeatures[idx]}')
                            
                            # Remove the pruned rule and the features assigned to it.
                            rules.pop(idx)
                            asgnFeatures.pop(idx)
                            mxPotQual.pop(idx)
                            
                            if idx <= rIdx:
                                rIdx -= 1
                            nRules -= 1
                        else:
                            idx += 1

            # Order the new rules based on their maximum potential quality.  The worst rules are
            # assigned the most child features.
            newRuleOrder = np.argsort(newRuleMxPotQual)
            newRules = [ newRules[i] for i in newRuleOrder ]
            newRuleMxPotQual = [ newRuleMxPotQual[i] for i in newRuleOrder ]

            
            
            # Determine which features to assign to each new rule for the creation
            # of their children.
            newRuleFeatures = []            
            for iR in range(len(newRules)):
            
                rNew = newRules[iR]
                
                # The feature used to create this new rule is removed from the list
                # of candidate child features.  The result is a fixed order search.
                childFeatures = childFeatures[childFeatures != rNew[-1]]
                prunedChildFeatures = []
                
                # Only actually copy features and prune redundancies if we're keeping this rule
                if newRuleMxPotQual[iR] >= bestQual:
                    
                                
                    # Remove any features that cover a superset of the new feature since
                    # the conjoint addition of those features won't change our coverage.
#                    prunedChildFeatures = copy.copy(childFeatures)

                    if len(childFeatures) > 0:

                        # Start by assuming all features are added.
                        addFtr = np.array([ False ]*covTblInfo.nFtr)
                        addFtr[childFeatures] = True

                        ruleAttr = covTblInfo.AttrInds[rNew[-1]]
                        ruleThresh = covTblInfo.ThreshVals[rNew[-1]]

                        # If this is a < feature, remove all other < features with a higher threshold.
                        if covTblInfo.Operators[rNew[-1]] == '<':
                            addFtr &= ~( (covTblInfo.AttrInds == ruleAttr) & (covTblInfo.ThreshVals > ruleThresh) & (covTblInfo.Operators == '<') )

                        # If this is a >= feature, remove all other >= features with a lower threshold.
                        else: 
                            addFtr &= ~( (covTblInfo.AttrInds == ruleAttr) & (covTblInfo.ThreshVals < ruleThresh) & (covTblInfo.Operators == '>=') )                    

                        #prunedChildFeatures = copy.copy(childFeatures[addFtr])
                        prunedChildFeatures = np.array(np.argwhere(addFtr)[:,0],dtype=np.ushort)

                        if self.debug == OPUS_DEBUG_EXHAUSTIVE:
                            if len(prunedChildFeatures) < len(childFeatures):
                                print(f'  {rNew}: Pruned {len(childFeatures)-len(prunedChildFeatures)} redundant features.')

                
                newRuleFeatures += [ prunedChildFeatures ]
                

            # Only keep new rules with the potential to beat the current best rule and that are shorter
            # than the maximum length.
            if self.debug == OPUS_DEBUG_EXHAUSTIVE:
                delInds = np.argwhere(np.array(newRuleMxPotQual) < bestQual)[:,0]
                for idx in delInds:
                    print(f' Pruned new rule: {newRules[idx]} (MxPotQual: {newRuleMxPotQual[idx]}, Features: {newRuleFeatures[idx]}')

            keepInds = np.argwhere(np.array(newRuleMxPotQual) >= bestQual)[:,0]    
            rules += [ newRules[i]  for i in keepInds ]    
            mxPotQual += [ newRuleMxPotQual[i]  for i in keepInds ]    
            asgnFeatures += [ newRuleFeatures[i]  for i in keepInds ]  
            
            rIdx += 1
            
            if self.debug == OPUS_DEBUG_EXHAUSTIVE:
                print(f'Best Rule: {bestRule} (Quality: {bestQual})\n')
            

        return bestRule
            
        
        
        
        
        
    
    
# ------- OPUS Rule Set Search -----------

def rule_set_search(ruleQual, ruleSearch, 
                    covTblInfo, covTbl, labels, idx=None, 
                    maxSetSize=1e300, coveredMultWeight=0, debug=False):
    """Uses a coverage approach to generate a rule set where OPUS is used to determine 
    the individual rules in the set.  Unless the maximum allowed set size is reached first,
    the routine terminates when all examples have been covered.
    
    -- Parameters --
     ruleQual: Reference to the RuleQuality derived class object used to calculate rule quality.
     ruleSearch: Reference to the object used to find the best individual rules.
     covTblInfo: Reference to a CoverageTableInformation object.
     covTbl: Numpy array of features.
     labels: Numpy array of labels.
     idx: Index of features to be used for training.
     maxSetSize: Maximum number of rules allowed in the set (defaults to infinite).
     coveredMultWeight: Weight used to multiply the label values of covered examples. 
       Defaults to 0 which completely removes an example the first time it's covered.
     debug: If true, produce debug output.
     """

    if idx is None:
        idx = list(range(len(labels)))
        
    
    ruleSet = []
    labels = copy.deepcopy(labels[idx])
    
    while np.sum(labels) > 0:

        if debug:
            print('Searching for individual rule...')
            
        newRule = ruleSearch.find_rule(covTblInfo,covTbl[idx,:],labels)
        
        if debug:
            print('\n-- New Rule --')
            ruleQual.print_summary([newRule],covTbl[idx,:],labels)
            print(f'Total Label Weight: {np.sum(labels)} (before), ',end='')
        
        dropExs = np.prod(covTbl[np.ix_(idx,newRule)],axis=1) == 1
        labels[dropExs] *= coveredMultWeight
        
        if debug:
            print(f'{np.sum(labels)} (after)\n')
        
        ruleSet += [ newRule ]

        if len(ruleSet) >= maxSetSize:
            break
        
    return ruleSet



# ------- RuleSet Cross Validation -----------

class RuleSetCrossValidation:
    '''Uses stratified k-fold cross-validation to evaluate a rule set's generalization error.
    '''
    def __init__(self,nSplit,ruleQual,ruleSearch,maxSetSize,debug=False,client=None):
        '''Initializes member variables.
        -- Parameters --
         nSplit: Number of splits for the k-fold algorithm.
         ruleQual: Rule quality object.
         ruleSearch: Rule search algorithm object.
         maxSetSize: Maximum rule set size.
         parallel: If true, execute using dask futures.
        '''
        
        self.nSplit = nSplit
        self.ruleQual = ruleQual
        self.ruleSearch = ruleSearch
        self.maxSetSize = maxSetSize
        self.debug = debug
        
        if client is None:
            self.parallel = False
        else:
            self.client = client
            _ = self.client.upload_file('../util/rules.py')
            self.parallel = True
                
        
    def cross_validate(self,covTblInfo,covTbl,labels):
        '''Perform cross-validation.
        -- Parameters --
         covTblInfo: CoverageTableInformation object with feature information.
         covTbl: Numpy coverage table array.
         labels: Numpy label vector.
        '''

        if self.parallel:
            return self.__cross_validate_parallel(covTblInfo,covTbl,labels)
        else:
            return self.__cross_validate_serial(covTblInfo,covTbl,labels)

    def __cross_validate_parallel(self,covTblInfo,covTbl,labels):
        '''Perform parallel processed cross-validation (CPU).
        -- Parameters --
         covTblInfo: CoverageTableInformation object with feature information.
         covTbl: Numpy coverage table array.
         labels: Numpy label vector.
        '''
        
        
        skf = StratifiedKFold(n_splits=self.nSplit, random_state=None, shuffle=True)

        covTblFtr = self.client.scatter(covTbl,broadcast=True)
        labelsFtr = self.client.scatter(labels,broadcast=True)

        
        futures = []
        for trainIdx, testIdx in skf.split(covTbl,labels):
            
            futures += [ 
                self.client.submit(
                    rule_set_search,
                    self.ruleQual, self.ruleSearch,
                    covTblInfo,covTblFtr,labelsFtr,
                    idx=trainIdx, maxSetSize=self.maxSetSize)
            ]
    
        ruleSets = self.client.gather(futures)   
                        
        self.ruleQual.size_head(len(testIdx))
        cnfMtx = np.zeros((2,2),dtype=int)
        for ruleSet in ruleSets:
            cnfMtx += self.ruleQual.confusion_matrix(ruleSet,covTbl[testIdx],labels[testIdx])
                
        return cnfMtx
    
        
    def __cross_validate_serial(self,covTblInfo,covTbl,labels):
        '''Perform single CPU serial cross-validation.
        -- Parameters --
         covTblInfo: CoverageTableInformation object with feature information.
         covTbl: Numpy coverage table array.
         labels: Numpy label vector.
        '''
        
        skf = StratifiedKFold(n_splits=self.nSplit, random_state=None, shuffle=True)

        cnfMtx = np.zeros((2,2),dtype=int)
        for trainIdx, testIdx in skf.split(covTbl,labels):
            
            if self.debug:
                print('-- Fold --')    
                
            self.ruleQual.size_head(len(trainIdx))
            ruleSet = rule_set_search(
                self.ruleQual,self.ruleSearch, 
                covTblInfo, covTbl, labels, idx=trainIdx, 
                maxSetSize=self.maxSetSize)
                                               
            self.ruleQual.size_head(len(testIdx))
            cnfMtxCur = self.ruleQual.confusion_matrix(ruleSet,covTbl[testIdx],labels[testIdx])
            
            if self.debug:
                print('\nRule Set: ',end='')
                self.ruleQual.print_summary(ruleSet,covTbl[testIdx],labels[testIdx])
                        
            cnfMtx += cnfMtxCur

        if self.debug:
            print('-- Final Confusion Matrix --')
            resStr = self.ruleQual.confusion_summary_str(cnfMtx, idnt=' ')
            print(resStr)
        
        return cnfMtx