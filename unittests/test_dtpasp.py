import unittest

import logging
logging.disable(level=logging.CRITICAL)

import aspmc.config as config
config.config["decos"] = "flow-cutter"
config.config["decot"] = "-1"

from aspmc.programs.dtpasprogram import DTPASProgram
import aspmc.semirings.maxmaxplusdecisions as semiring



def cb(program):
    program.tpUnfold()
    program.td_guided_both_clark_completion()

class DTPASPTest(unittest.TestCase):
    
    def test_dtpasp_long(self):
        config.config["knowledge_compiler"] = "c2d"
        config.config["constrained"] = "XD"
        program = DTPASProgram("", ["./test/test_dtpasp_long.lp"])
        cb(program)
        self.assertEqual(len(program.get_queries()), 0)
        cnf = program.get_cnf()
        results = cnf.evaluate()
        self.assertEqual(len(results), 1)
        atom_idx = semiring.names.index("da(0)")
        expected_decisions = (0, 2**atom_idx)
        self.assertEqual(results[0].decisions, expected_decisions)
        expected_values = (0.0, 1.9435049502)
        self.assertAlmostEqual(results[0].value[0], expected_values[0])
        self.assertAlmostEqual(results[0].value[1], expected_values[1])

    def test_dtpasp_short1(self):
        config.config["knowledge_compiler"] = "c2d"
        config.config["constrained"] = "XD"
        program = DTPASProgram("", ["./test/test_dtpasp_short1.lp"])
        cb(program)
        self.assertEqual(len(program.get_queries()), 0)
        cnf = program.get_cnf()
        results = cnf.evaluate()
        self.assertEqual(len(results), 1)
        atom0_idx = semiring.names.index("da(0)")
        atom1_idx = semiring.names.index("da(1)")
        expected_decisions = (2**atom0_idx + 2**atom1_idx, 2**atom0_idx + 2**atom1_idx)
        self.assertEqual(results[0].decisions, expected_decisions)
        expected_values = (0.6, 0.6)
        self.assertAlmostEqual(results[0].value[0], expected_values[0])
        self.assertAlmostEqual(results[0].value[1], expected_values[1])

    def test_dtpasp_short2(self):
        config.config["knowledge_compiler"] = "c2d"
        config.config["constrained"] = "XD"
        program = DTPASProgram("", ["./test/test_dtpasp_short2.lp"])
        cb(program)
        self.assertEqual(len(program.get_queries()), 0)
        cnf = program.get_cnf()
        results = cnf.evaluate()
        self.assertEqual(len(results), 1)
        atom_idx = semiring.names.index("da(0)")
        expected_decisions = (0, 2**atom_idx)
        self.assertEqual(results[0].decisions, expected_decisions)
        expected_values = (0.0, 1.02)
        self.assertAlmostEqual(results[0].value[0], expected_values[0])
        self.assertAlmostEqual(results[0].value[1], expected_values[1])

    def test_X_constrained(self):
        config.config["knowledge_compiler"] = "c2d"
        config.config["constrained"] = "X"
        program = DTPASProgram("", ["./test/test_dtpasp_long.lp"])
        cb(program)
        self.assertEqual(len(program.get_queries()), 0)
        cnf = program.get_cnf()
        results = cnf.evaluate()
        self.assertEqual(len(results), 1)
        atom_idx = semiring.names.index("da(0)")
        expected_decisions = (0, 2**atom_idx)
        self.assertEqual(results[0].decisions, expected_decisions)
        expected_values = (0.0, 1.9435049502)
        self.assertAlmostEqual(results[0].value[0], expected_values[0])
        self.assertAlmostEqual(results[0].value[1], expected_values[1])



if __name__ == '__main__':
    unittest.main(buffer=True)
