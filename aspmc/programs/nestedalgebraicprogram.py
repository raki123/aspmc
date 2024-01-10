"""
Program module providing the nested algebraic progam class.
"""

import numpy as np

from aspmc.programs.program import Program

from aspmc.util import *

class NestedAlgebraicProgram(Program):    
    """A class for programs with weights over more than two semirings. 

    This is supposed to be an abstract class in the sense that it should used and instantiated
    by subclasses, rather than parsed itself.

    Overrides the `get_weights`, `_finalize_cnf` and `get_queries` methods appropriately.

    Args:
        clingo_control (:obj:`Control`): The clingo control object having the rules of the spanning program.
        semirings (:obj:`list[module]`): The list of semiring modules.
        weights (:obj:`list[dict]`): The list of weights over the semirings in order of the semirings. 
            Needs to map pairs `(name, phase)`, where `name` is the name of an atom 
            and `phase` is its polarity (`True` for true), to their weight.
        transforms (:obj:`list[string]`): A list of string representations of the functions that transforms a value 
            from the ith into a value from the (i-1)th semiring.
        queries (:obj:`list`): A list of names of atoms that should be queried. 
            Specify the empty list for an overall weight query.

    Attributes:
        semirings (:obj:`list[module]`): The list of semiring modules.
        weights (:obj:`list[dict]`): The list of weights over the semirings in order of the semirings. 
            Needs to map pairs `(name, phase)`, where `name` is the name of an atom 
            and `phase` is its polarity (`True` for true), to their weight.
        transforms (:obj:`list[string]`): A list of string representations of the functions that transforms a value 
            from the ith into a value from the (i-1)th semiring.
        queries (:obj:`list`): A list of names of atoms that should be queried. 
            Specify the empty list for an overall weight query.
    """
    def __init__(self, clingo_control, semirings, weights_per_semiring, transforms, queries):
        self.semirings = semirings
        self.weights_per_semiring = weights_per_semiring
        self.transforms = transforms
        self.queries = queries
        Program.__init__(self, clingo_control = clingo_control)

    def _finalize_cnf(self):
        weight_list = self.get_weights()
        varMap = { name : var for var, name in self._nameMap.items() }
        # quantifiers
        self._cnf.quantified = []
        for cur_weights in self.weights_per_semiring:
            cur_atoms = set([ int(str(varMap[name])) for (name, _) in cur_weights ])
            self._cnf.quantified.append(cur_atoms)
        # weights
        for v in range(self._cnf.nr_vars*2):
            self._cnf.weights[to_dimacs(v)] = weight_list[v]
        # rest
        self._cnf.transforms = self.transforms
        self._cnf.semirings = self.semirings
        # TODO figure out which variables we can mark as auxilliary

    def get_weights(self):
        query_cnt = max(len(self.get_queries()), 1)
        shapes = [ (query_cnt, ) + np.shape(semiring.one()) for semiring in self.semirings ]
        varMap = { name : var for var, name in self._nameMap.items() }
        # default initialize with innermost semirings one
        weight_list = [ np.empty(shapes[-1], dtype=self.semirings[-1].dtype) for _ in range(self._cnf.nr_vars*2) ]
        for i in range(self._cnf.nr_vars*2):
            weight_list[i][:] = self.semirings[-1].one()
        for i, cur_weights in enumerate(self.weights_per_semiring):
            for (name, phase) in cur_weights:
                idx = to_pos(varMap[name])
                if not phase:
                    idx = neg(idx)
                weight_list[idx] = np.empty(shapes[i], dtype=self.semirings[i].dtype)
                weight_list[idx][:] = cur_weights[(name, phase)]
                
        
        if len(self.get_queries()) == 0:
            return weight_list
        
        # set the weights for the queries
        var_to_val_type = [ len(self.semirings) - 1 for _ in range(self._cnf.nr_vars + 1) ]
        for val_type, cur_weights in enumerate(self.weights_per_semiring):
            for (name, _) in cur_weights:
                var = int(str(varMap[name]))
                var_to_val_type[var] = val_type
                
        for i, query in enumerate(self.get_queries()):
            var = int(str(varMap[query]))
            val_type = var_to_val_type[var]
            zero = self.semirings[val_type].zero()
            weight_list[neg(to_pos(varMap[query]))][i] = zero
            
        return weight_list

    def get_queries(self):
        return self.queries
