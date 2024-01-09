"""
Program module providing the two algebraic progam class.
"""
import numpy as np

import logging
logger = logging.getLogger("aspmc")

from aspmc.programs.program import Program

from aspmc.util import *

class TwoAlgebraicProgram(Program):    
    """A class for programs with weights over two semirings. 

    This is supposed to be an abstract class in the sense that it should used and instantiated
    by subclasses, rather than parsed itself.

    Overrides the `get_weights`, `_finalize_cnf` and `get_queries` methods appropriately.

    Args:
        clingo_control (:obj:`Control`): The clingo control object having the rules of the spanning program.
        first_semiring (:obj:`module`): The first semiring module.
        second_semiring (:obj:`module`): The second semiring module.
        first_weights (:obj:`dict`): The weights over the first semiring. 
            Needs to map pairs `(name, phase)`, where `name` is the name of an atom 
            and `phase` is its polarity (`True` for true), to their weight.
        second_weights (:obj:`dict`): The weights over the second semiring. 
            Needs to map pairs `(name, phase)`, where `name` is the name of an atom 
            and `phase` is its polarity (`True` for true), to their weight.
        transform (:obj:`string`): A string representation of the function that transforms a value from the first
            into a value from the second semiring.
        queries (:obj:`list`): A list of names of atoms that should be queried. 
            Specify the empty list for an overall weight query.

    Attributes:
        first_semiring (:obj:`module`): The first semiring module.
        second_semiring (:obj:`module`): The second semiring module.
        first_weights (:obj:`dict`): The weights over the first semiring. 
            Needs to map pairs `(name, phase)`, where `name` is the name of an atom 
            and `phase` is its polarity (`True` for true), to their weight.
        second_weights (:obj:`dict`): The weights over the second semiring. 
            Needs to map pairs `(name, phase)`, where `name` is the name of an atom 
            and `phase` is its polarity (`True` for true), to their weight.
        transform (:obj:`string`): A string representation of the function that transforms a value from the first
            into a value from the second semiring.
        queries (:obj:`list`): A list of names of atoms that should be queried. 
            Specify the empty list for an overall weight query.
    """
    def __init__(self, clingo_control, first_semiring, second_semiring, first_weights, second_weights, transform, queries):
        logger.warning("TwoAlgebraicProgram may be removed in favor of the new NestedAlgebraicProgram in the future")
        self.first_semiring = first_semiring
        self.second_semiring = second_semiring
        self.first_weights = first_weights
        self.second_weights = second_weights
        self.transform = transform
        self.queries = queries
        Program.__init__(self, clingo_control = clingo_control)

    def _finalize_cnf(self):
        weight_list = self.get_weights()
        varMap = { name : var for var, name in self._nameMap.items() }
        first = set([ int(str(varMap[name])) for (name, _) in self.first_weights ])
        second = set([ int(str(varMap[name])) for (name, _) in self.second_weights ])
        self._cnf.quantified = [first, second]
        for v in range(self._cnf.nr_vars*2):
            self._cnf.weights[to_dimacs(v)] = weight_list[v]
        self._cnf.transforms = [ self.transform ]
        self._cnf.semirings = [ self.first_semiring, self.second_semiring ]
        # TODO figure out which variables we can mark as auxilliary

    def get_weights(self):
        query_cnt = max(len(self.get_queries()), 1)
        first_shape = (query_cnt, ) + np.shape(self.first_semiring.one())
        second_shape = (query_cnt, ) + np.shape(self.second_semiring.one())
        varMap = { name : var for var, name in self._nameMap.items() }
        weight_list = [ np.empty(second_shape, dtype=self.second_semiring.dtype) for _ in range(self._cnf.nr_vars*2) ]
        for i in range(self._cnf.nr_vars*2):
            weight_list[i][:] = self.second_semiring.one()
        for (name, phase) in self.first_weights:
            idx = to_pos(varMap[name])
            if not phase:
                idx = neg(idx)
            weight_list[idx] = np.empty(first_shape, dtype=self.first_semiring.dtype)
            weight_list[idx][:] = self.first_weights[(name, phase)]
        for (name, phase) in self.second_weights:            
            idx = to_pos(varMap[name])
            if not phase:
                idx = neg(idx)
            weight_list[idx] = np.empty(second_shape, dtype=self.second_semiring.dtype)
            weight_list[idx][:] = self.second_weights[(name, phase)]
        for i, query in enumerate(self.get_queries()):
            if (query, True) in self.first_weights:
                weight_list[neg(to_pos(varMap[query]))][i] = self.first_semiring.zero()
            else:
                weight_list[neg(to_pos(varMap[query]))][i] = self.second_semiring.zero()
        return weight_list

    def get_queries(self):
        return self.queries
