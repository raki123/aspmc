import unittest

import logging
logging.disable(level=logging.CRITICAL)

import aspmc.config as config
config.config["decos"] = "flow-cutter"
config.config["decot"] = "-1"

from aspmc.programs.credalprogram import CredalProgram
import aspmc.semirings.credal as semiring


def cb(program):
    program.tpUnfold()
    program.td_guided_both_clark_completion()

class TestCredal(unittest.TestCase):
    
    def test_credal_semantics(self):
        config.config["knowledge_compiler"] = "c2d"
        config.config["constrained"] = "XD"
        program = CredalProgram("", ["./test/test_credal_small.lp"])
        cb(program)
        self.assertEqual(len(program.get_queries()), 1)
        cnf = program.get_cnf()
        results = cnf.evaluate()
        self.assertEqual(len(results), 1)
        expected = {
            "b" : semiring.from_value((0.5, 1.0))
        }
        for i, query in enumerate(program.get_queries()):
            self.assertEqual(len(results[i]), 2)
            self.assertAlmostEqual(results[i][0], expected[query][0])
            self.assertAlmostEqual(results[i][1], expected[query][1])

    def test_smokers_10(self):
        program = CredalProgram("", ["./test/test_smokers_10.lp"])
        cb(program)
        self.assertEqual(len(program.get_queries()), 10)
        cnf = program.get_cnf()
        config.config["knowledge_compiler"] = "c2d"
        config.config["constrained"] = "XD"
        results = cnf.evaluate()
        defined = cnf.get_defined(cnf.quantified[0])
        self.assertEqual(len(defined) + len(cnf.quantified[0]), cnf.nr_vars)
        self.assertEqual(len(results), 10)
        expected = [ 
            0.845642576843858, 0.7061644677402408, 0.9080926252529147, 0.9060131023306259,
            0.8940463791307754, 0.6329668151001511, 0.5492261840660287, 0.9165727398797205,
            0.7925499302372165, 0.49999999999999994
        ]
        expected = [ semiring.from_value((v,v)) for v in expected ]
        for i in range(10):
            self.assertEqual(len(results[i]), 2)
            self.assertAlmostEqual(results[i][0], expected[i][0])
            self.assertAlmostEqual(results[i][1], expected[i][1])
        config.config["knowledge_compiler"] = "miniC2D"
        config.config["constrained"] = "XD"
        results = cnf.evaluate()
        self.assertEqual(len(results), 10)
        for i in range(10):
            self.assertEqual(len(results[i]), 2)
            self.assertAlmostEqual(results[i][0], expected[i][0])
            self.assertAlmostEqual(results[i][1], expected[i][1])

    def test_X_constrained(self):
        program = CredalProgram("", ["./test/test_sm_small.lp"])
        cb(program)
        self.assertEqual(len(program.get_queries()), 1)
        cnf = program.get_cnf()
        config.config["knowledge_compiler"] = "c2d"
        config.config["constrained"] = "X"
        results = cnf.evaluate()
        self.assertEqual(len(results), 1)
        expected = {
            "c" : semiring.from_value((0.7, 0.7))
        }
        for i, query in enumerate(program.get_queries()):
            self.assertEqual(len(results[i]), 2)
            self.assertAlmostEqual(results[i][0], expected[query][0])
            self.assertAlmostEqual(results[i][1], expected[query][1])
        config.config["knowledge_compiler"] = "miniC2D"
        config.config["constrained"] = "X"
        results = cnf.evaluate()
        self.assertEqual(len(results), 1)
        for i, query in enumerate(program.get_queries()):
            self.assertEqual(len(results[i]), 2)
            self.assertAlmostEqual(results[i][0], expected[query][0])
            self.assertAlmostEqual(results[i][1], expected[query][1])



if __name__ == '__main__':
    unittest.main(buffer=True)
