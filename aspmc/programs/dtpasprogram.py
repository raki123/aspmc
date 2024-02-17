#!/usr/bin/env python3

"""
Maximum Expected Utility ASProgram module specializing the NestedAlgebraicProgam class.
"""
import logging

from aspmc.parsing.clingoparser.clingoext import Control

from aspmc.programs.problogprogram import ProblogProgram
from aspmc.programs.nestedalgebraicprogram import NestedAlgebraicProgram
from lark import Lark
from aspmc.parsing.lark_parser import GRAMMAR, ProblogTransformer
from aspmc.util import *

import aspmc.semirings.maxmaxplusdecisions as first_semiring
import aspmc.semirings.twograd as second_semiring # the gradient semiring and the expected utility are the same
import aspmc.semirings.minmaxplus as third_semiring 
import aspmc.semirings.probabilistic as semiring

logger = logging.getLogger("aspmc")

class DTPASProgram(NestedAlgebraicProgram, ProblogProgram):
    """A class for Maximum Expected Utility programs. 

    The syntax for these programs is the same as for ProbLog in MEU mode. 
    This means that the probabilistic part is specified as usual,
    utility atoms `a`, i.e. atoms whose truth adds utility value `u` to the model, must be given as `utility(a, u).` and
    the decision atoms `d`, whose assignment should be maximized over should be given as `decision(d).`.

    Subclasses `TwoAlgebraicProgram` since it is a second level problem.

    Overrides the `_prepare_grounding` method to deal with utilities and decisions.

    Args:
        program_str (:obj:`string`): A string containing a part of the program in MEU ProbLog syntax. 
        May be the empty string.
        program_files (:obj:`list`): A list of string that are paths to files which contain programs in 
        MEU ProbLog syntax that should be included. May be an empty list.
    """
    def __init__(self, program_str, program_files):
        self.semiring = semiring
        self.weights = {}
        self.utilities = {}
        self.decisions = []
        self.queries = []
        self.annotated_disjunctions = []
        for path in program_files:
            with open(path) as file_:
                program_str += file_.read()
        
        # parse the program
        my_grammar = GRAMMAR + f"""
        QUESTION_MARK : "?"
        %override weight : /{self.semiring.pattern}/ | variable | QUESTION_MARK
        """
        parser = Lark(my_grammar, start='program', parser='lalr', transformer=ProblogTransformer())
        program = parser.parse(program_str)

        # ground the program
        clingo_control = Control()
        self._ground(clingo_control, program)

        # set the weights
        first_weight_list = {}
        # weights for the maxplus semiring
        first_semiring.names = [ name for name in self.decisions ]
        for i,name in enumerate(self.decisions):
            first_weight_list[(name, True)] = first_semiring.MinMaxPlusFloat((0, 0), (2**i, 2**i))
            first_weight_list[(name, False)] = first_semiring.one()
        # weights for the expected utility semiring
        second_weight_list = {}
        for name in self.weights:
            second_weight_list[(name, True)] = [self.weights[name], 0.0]
            second_weight_list[(name, False)] = [1.0 - self.weights[name], 0.0]
        third_weight_list = {}
        for (name, phase) in self.utilities:
            if (name, phase) in second_weight_list:
                if (name, phase) in first_weight_list:
                    logger.error(f"Variable {name} cannot be both a decision and probabilistic variable.")
                    exit(-1)
                second_weight_list[(name, phase)][1] = second_weight_list[(name, phase)][0]*self.utilities[(name, phase)]
            elif (name, phase) in first_weight_list:
                first_weight_list[(name, phase)].value[0] = self.utilities[(name, phase)]
                first_weight_list[(name, phase)].value[1] = self.utilities[(name, phase)]
            else:
                third_weight_list[(name, phase)] = self.utilities[(name, phase)]
        second_weight_list = { i : second_semiring.parse(f"({w[0]},{w[1]},{w[1]})") for (i, w) in second_weight_list.items() }
        third_weight_list = { i : third_semiring.parse(f"({w},{w})") for (i, w) in third_weight_list.items() }

        semirings = [ first_semiring, second_semiring, third_semiring ]
        weights_per_semiring = [ first_weight_list, second_weight_list, third_weight_list ]
        transforms = [ "lambda w : (w.value[1], w.value[2])", "lambda w : (1.0, w.value[0], w.value[1])" ]
        NestedAlgebraicProgram.__init__(self, clingo_control, semirings, weights_per_semiring, transforms, self.queries)

    def _prepare_grounding(self, program):
        new_program = []
        for r in program:
            if isinstance(r, str):
                new_program.append(r)
            elif r.weights is not None and r.weights[0] == '?':
                atom = r.head[0]
                self.decisions.append(str(atom))
                new_program.append(f"{{{atom}}}.")
            elif r.head is not None and r.head[0].predicate == "utility":
                atom = r.head[0].inputs[0]
                utility = r.head[0].inputs[1]
                phase = True
                if atom.negated:
                    phase = False
                    atom.negated = False
                self.utilities[(str(atom), phase)] = float(utility)
            elif r.head is not None and r.head[0].predicate == "query":
                atom = r.head[0].inputs[0]
                logger.warning(f"Ignoring query for atom {atom}.")
            else:
                new_program.append(r)
        return super()._prepare_grounding(new_program)

    def _prog_string(self, program):
        result = ""
        for v in self._guess:
            if self._internal_name(v) in self.decisions:
                result += f"?::{self._external_name(v)}.\n"
            else:
                result += f"{self.weights[self._internal_name(v)]}::{self._external_name(v)}.\n"
        for (name, phase) in self.utilities:
            result += "utility("
            if not phase:
                result += "\\+"
            result += f"{name}, {self.utilities[(name, phase)]}).\n"
        for r in program:
            result += ";".join([self._external_name(v) for v in r.head])
            if len(r.body) > 0:
                result += ":-"
                result += ",".join([("\\+" if v < 0 else "") + self._external_name(abs(v)) for v in r.body])
            result += ".\n"
        for query in self.queries:
            result += f"query({query}).\n"
        return result