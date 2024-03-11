#!/usr/bin/env python3

"""
Program module providing the credal program class.
"""
import logging
import numpy as np

from aspmc.parsing.clingoparser.clingoext import Control

from aspmc.programs.problogprogram import ProblogProgram
from aspmc.programs.nestedalgebraicprogram import NestedAlgebraicProgram
from lark import Lark
from aspmc.parsing.lark_parser import GRAMMAR, ProblogTransformer, ProbabilisticRule, Atom
from aspmc.util import *

import aspmc.semirings.probabilistic as parse_semiring
import aspmc.semirings.credal as semiring

import aspmc.config as config

logger = logging.getLogger("aspmc")

class CredalProgram(NestedAlgebraicProgram, ProblogProgram):    
    """A class for CredalProgram programs. 

    Subclasses `NestedAlgebraicProgram` since it is a second level problem.

    Overrides the `_prepare_grounding` method to deal with negative atoms in the head in the same way as ProbLog.

    Args:
        program_str (:obj:`string`): A string containing a part of the program in ProbLog syntax. 
        May be the empty string.
        program_files (:obj:`list`): A list of string that are paths to files which contain programs in 
        ProbLog syntax that should be included. May be an empty list.
    """
    def __init__(self, program_str, program_files):
        self.semiring = parse_semiring
        self.weights = {}
        self.queries = []
        self.annotated_disjunctions = []
        for path in program_files:
            with open(path) as file_:
                program_str += file_.read()

        # parse the program
        my_grammar = GRAMMAR + f"%override weight : /{self.semiring.pattern}/ | variable\n"
        parser = Lark(my_grammar, start='program', parser='lalr', transformer=ProblogTransformer())
        program = parser.parse(program_str)

        # ground the program
        clingo_control = Control()
        self._ground(clingo_control, program)

        # initialize weights
        weight_list = {}
        for name in self.weights:
            weight_list[(name, True)] = (self.weights[name], self.weights[name])
            weight_list[(name, False)] = (1 - self.weights[name], 1 - self.weights[name])

        self.first_weights = weight_list

        semirings = [ semiring, semiring ]
        weights_per_semiring = [ weight_list, {} ]
        transforms = [ "lambda w : (float(w[0] == w[1] and w[0] > 0), float(w[0] > 0))" ]
        NestedAlgebraicProgram.__init__(self, clingo_control, semirings, weights_per_semiring, transforms, self.queries)

    def _prepare_grounding(self, program):
        # take care of the transformation for negated head atoms
        # first gather all the head atoms grouped by whether they are negated and their predicate
        program = list(program)
        predicate_to_pos_heads = {}
        predicate_to_neg_heads = {}
        for r in program:
            if isinstance(r, str):
                program.append(r)
            elif r.head is not None:
                for a in r.head:
                    if a.negated:
                        if not a.predicate in predicate_to_neg_heads:
                            predicate_to_neg_heads[a.predicate] = []
                        predicate_to_neg_heads[a.predicate].append(a)
                    else:
                        if not a.predicate in predicate_to_pos_heads:
                            predicate_to_pos_heads[a.predicate] = []
                        predicate_to_pos_heads[a.predicate].append(a)
        
        
        # next, for every predicate pred that occurs negated introduce two new predicates pos_pred, neg_pred
        # derive pred only of pos_pred but not neg_pred holds
        for pred in predicate_to_neg_heads:
            arities = set()
            for atom in predicate_to_neg_heads[pred]:
                atom.predicate = f"neg_{pred}"
                atom.negated = False
                arities.add(len(atom.inputs))
            for atom in predicate_to_pos_heads[pred]:
                if len(atom.inputs) in arities: # otherwise we can trust that we really derive the positive version anyway
                    atom.predicate = f"pos_{pred}"
            for l in arities:
                head = [ Atom(pred, [ f"X{i}" for i in range(l) ], negated = False) ]
                body = [ 
                    Atom(f"pos_{pred}", [ f"X{i}" for i in range(l) ], negated = False),  
                    Atom(f"neg_{pred}", [ f"X{i}" for i in range(l) ], negated = True)
                    ]
                rule = ProbabilisticRule(head, body, weights = None)
                program.append(rule)
        return super()._prepare_grounding(program)

    def _prog_string(self, program):
        result = ""
        for v in self._guess:
            result += f"{self.weights[self._internal_name(v)]}::{self._external_name(v)}.\n"
        for r in program:
            result += ";".join([self._external_name(v) for v in r.head])
            if len(r.body) > 0:
                result += ":-"
                result += ",".join([("\\+ " if v < 0 else "") + self._external_name(abs(v)) for v in r.body])
            result += ".\n"
        for query in self.queries:
            result += f"query({query}).\n"
        return result
    
    def get_weights(self):
        varMap = { name : var for var, name in self._nameMap.items() }
        weight_list = super().get_weights()
        for i, query in enumerate(self.queries):
            if (query, True) in self.first_weights:
                weight_list[neg(to_pos(varMap[query]))][i] = self.semiring.zero()
            else:
                weight_list[neg(to_pos(varMap[query]))][i] = np.array([0.0, 1.0])
        return weight_list