#!/usr/bin/env python3

"""
Main module providing the application logic.
"""

import sys
import logging
import importlib


from aspmc.programs.program import Program
from aspmc.programs.problogprogram import ProblogProgram
from aspmc.programs.algebraicprogram import AlgebraicProgram
from aspmc.programs.smprogram import SMProblogProgram
from aspmc.programs.meuprogram import MEUProblogProgram
from aspmc.programs.mapprogram import MAPProblogProgram
from aspmc.programs.mpeprogram import MPEProblogProgram
from aspmc.programs.optprogram import OptProgram
from aspmc.programs.dtpasprogram import DTPASProgram
from aspmc.programs.credalprogram import CredalProgram

from aspmc.compile.cnf import CNF

from aspmc.graph.treedecomposition import from_hypergraph

import aspmc.config as config

import aspmc.signal_handling

logger = logging.getLogger("aspmc")
logging.basicConfig(format='[%(levelname)s] %(name)s: %(message)s', level="INFO")

def addLoggingLevel(levelName, levelNum, methodName=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present 

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
       raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
       raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
       raise AttributeError('{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)
    
addLoggingLevel("RESULT", logging.INFO + 5)
logger.setLevel(logging.INFO)

help_string = """
aspmc: An Algebraic Answer Set Counter
aspmc version 1.1.0, Mar 11, 2024

python main.py [-m .] [-st .] [-c] [-s .] [-n] [-t] [-ds .] [-dt .] [-k .] [-g .] [-b .] [-v .] [-h] [<INPUT-FILES>]
    --mode              -m  MODE        set input mode to MODE:
                                        * asp               : take a normal answer set program as input (default)
                                        * smodels           : take a normal answer set program in smodels format as input
                                        * optasp            : take a normal answer set program with weak constraints as input
                                        * cnf               : take an (extended) cnf as input
                                        * problog           : take a problog program as input
                                        * smproblog         : take a problog program with negations as input
                                        * meuproblog        : take a problog program with extra decision and utility atoms as input
                                        * mapproblog        : take a problog program with extra evidence and map query atoms as input
                                        * mpeproblog        : take a problog program with extra evidence atoms as input
                                        * dtpasp            : take a probabilistic answer set program with extra decision and utility atoms as input
                                        * credal            : take a probabilistic answer set program with credal semantics as input
    --strategy          -st STRATEGY    set solving strategy to STRATEGY:
                                        * flexible          : choose the solver flexibly 
                                        * compilation       : use knowledge compilation (default)
    --count             -c              not only output the equivalent cnf as out.cnf but also performs (algebraic) counting of the answer sets
    --semiring          -s  SEMIRING    use the semiring specified in the python file aspmc/semirings/SEMIRING.py
                                        only useful with -m problog
    --no_pp             -n              does not perform cycle breaking and outputs a normalized version of the input program as `out.lp`
                                        the result is equivalent, ground and does not contain annotated disjunctions.
    --treewidth         -t              print the treewidth of the resulting CNF
    --decos             -ds SOLVER      set the solver that computes tree decompositions to SOLVER:
                                        * flow-cutter       : uses flow_cutter_pace17 (default)
    --decot             -dt SECONDS     set the timeout for computing tree decompositions to SECONDS (default: 1)
    --knowlege          -k  COMPILER    set the knowledge compiler to COMPILER:
                                        * sharpsat-td       : uses a compilation version of sharpsat-td (default)
                                        * sharpsat-td-live  : uses a compilation version of sharpsat-td where compilation and counting are simultaneous
                                        * d4                : uses the (slightly modified) d4 compiler. 
                                        * c2d               : uses the c2d compiler. 
                                        * miniC2D           : uses the miniC2D compiler. 
    --guide_clark       -g  GUIDE       set the tree decomposition type to use to guide the clark completion to GUIDE:
                                        * none              : preform the normal clark completion without guidance
                                        * ors               : guide for or nodes only 
                                        * both              : guide for both `and` and `or` nodes (default)
                                        * adaptive          : guide `both` that takes into account the cost of auxilliary variables 
                                        * choose            : try to choose the best of the previous options bases on expected treewidth
    --cycle-breaking    -b  STRATEGY    set the cycle-breaking strategy to STRATEGY:
                                        * none              : do not perform cycle-breaking, not suitable for model counting
                                        * tp                : perform tp-unfolding, suitable for model counting (default)
                                        * binary            : use the strategy of Janhunen without local and global ranking constraints
                                                                not suitable for model counting
                                        * binary-opt        : use the strategy of Hecher, not suitable for model counting
                                        * lt                : use the strategy of Lin and Zhao, not suitable for model counting
                                        * lt-opt            : use a modified version of Lin and Zhao's strategy with a smaller encoding,
                                                                not suitable for model counting
    --verbosity         -v  VERBOSITY   set the logging level to VERBOSITY:
                                        * debug             : print everything
                                        * info              : print as usual
                                        * result            : only print results, warnings and errors
                                        * warning           : only print warnings and errors
                                        * errors            : only print errors
    --help              -h              print this help and exit
"""

def main():
    mode = "asp"
    cycle_breaking = "tp"
    program_files = []
    program_str = ""
    count = False
    preprocessing = False
    no_pp = False
    write_name = ""
    treewidth = False
    semiring_string = "aspmc.semirings.probabilistic"
    guide = "both"
    strategy = "flexible"
    smodels = False

    # parse the arguments
    while len(sys.argv) > 1:
        if sys.argv[1].startswith("-"):
            if sys.argv[1] == "-m" or sys.argv[1] == "--mode":
                mode = sys.argv[2]
                if mode != "problog" and mode != "asp" and mode != "smproblog" and mode != "meuproblog" \
                    and mode != "mapproblog" and mode != "mpeproblog" and mode != "optasp" and mode != "cnf" \
                    and mode != "smodels" and mode != "dtpasp" and mode != "credal":
                    logger.error("  Unknown mode: " + mode)
                    exit(-1)
                smodels = mode == "smodels"
                del sys.argv[1:3]
            elif sys.argv[1] == "-st" or sys.argv[1] == "--strategy":
                strategy = sys.argv[2]
                if strategy != "flexible" and strategy != "compilation":
                    logger.error("  Unknown strategy: " + strategy)
                    exit(-1)
                del sys.argv[1:3]
            elif sys.argv[1] == "-b" or sys.argv[1] == "--cycle-breaking":
                cycle_breaking = sys.argv[2]
                if cycle_breaking != "tp" and cycle_breaking != "binary" and cycle_breaking != "binary-opt" \
                    and cycle_breaking != "lt" and cycle_breaking != "lt-opt" and cycle_breaking != "none":
                    logger.error("  Unknown cycle breaking: " + cycle_breaking)
                    exit(-1)
                del sys.argv[1:3]
            elif sys.argv[1] == "-c" or sys.argv[1] == "--count":
                count = True
                del sys.argv[1]
            elif sys.argv[1] == "-p" or sys.argv[1] == "--preproc":
                preprocessing = True
                del sys.argv[1]
            elif sys.argv[1] == "-s" or sys.argv[1] == "--semiring":
                logger.info(f"   Using semiring {sys.argv[2]}.")
                semiring_string = f"aspmc.semirings.{sys.argv[2]}"
                del sys.argv[1:3]            
            elif sys.argv[1] == "-n" or sys.argv[1] == "--no_pp":
                no_pp = True
                del sys.argv[1]
            elif sys.argv[1] == "-t" or sys.argv[1] == "--treewidth":
                treewidth = True
                del sys.argv[1]
            elif sys.argv[1] == "-w" or sys.argv[1] == "--write":
                write_name = sys.argv[2]
                del sys.argv[1:3]
            elif sys.argv[1] == "-v" or sys.argv[1] == "--verbosity":
                verbosity = sys.argv[2].upper()
                if verbosity != "DEBUG" and verbosity != "INFO" and verbosity != "RESULT" and verbosity != "WARNING" and verbosity != "ERROR":
                    logger.error("  Unknown verbosity: " + verbosity)
                    exit(-1)
                logger.setLevel(verbosity)
                del sys.argv[1:3]
            elif sys.argv[1] == "-ds" or sys.argv[1] == "--decos":
                if sys.argv[2] != "flow-cutter":
                    logger.error("  Unknown tree decomposer: " + sys.argv[2])
                    exit(-1)
                config.config["decos"] = sys.argv[2]
                del sys.argv[1:3]
            elif sys.argv[1] == "-dt" or sys.argv[1] == "--decot":
                config.config["decot"] = sys.argv[2]
                del sys.argv[1:3]            
            elif sys.argv[1] == "-k" or sys.argv[1] == "--knowledge_compiler":
                config.config["knowledge_compiler"] = sys.argv[2]
                if sys.argv[2] != "c2d" and sys.argv[2] != "miniC2D" and sys.argv[2] != "sharpsat-td" and sys.argv[2] != "sharpsat-td-live" and sys.argv[2] != "d4":
                    logger.error("  Unknown knowledge compiler: " + sys.argv[2])
                    exit(-1)
                del sys.argv[1:3]
            elif sys.argv[1] == "-g" or sys.argv[1] == "--guide_clark":
                guide = sys.argv[2]
                if sys.argv[2] != "none" and sys.argv[2] != "ors" and sys.argv[2] != "both" and sys.argv[2] != "adaptive" and sys.argv[2] != "choose":
                    logger.error("  Unknown guide: " + sys.argv[2])
                    exit(-1)
                del sys.argv[1:3]
            elif sys.argv[1] == "-h" or sys.argv[1] == "--help":
                logger.info(help_string)
                exit(0)
            else:
                logger.error("  Unknown option: " + sys.argv[1])
                logger.info(help_string)
                exit(-1)
        else:
            program_files.append(sys.argv[1])
            del sys.argv[1]

    semiring = importlib.import_module(semiring_string)
    # parse the input 
    if not program_files:
        program_str = sys.stdin.read()
    if mode == "problog":
        if semiring.__name__ == "aspmc.semirings.probabilistic":
            program = ProblogProgram(program_str, program_files)
        else:
            program = AlgebraicProgram(program_str, program_files, semiring)
    elif mode == "smproblog":
        program = SMProblogProgram(program_str, program_files)
    elif mode == "meuproblog":
        program = MEUProblogProgram(program_str, program_files)
    elif mode == "mapproblog":
        program = MAPProblogProgram(program_str, program_files)
    elif mode == "mpeproblog":
        program = MPEProblogProgram(program_str, program_files)
    elif mode == "dtpasp":
        program = DTPASProgram(program_str, program_files)
    elif mode == "credal":
        program = CredalProgram(program_str, program_files)
    elif mode == "optasp":
        program = OptProgram(program_str, program_files)
    elif mode == "cnf":
        if len(program_files) > 0:
            cnf = CNF(path = program_files[0])
        else:
            cnf = CNF(string = program_str)
    else:
        program = Program(program_str = program_str, program_files = program_files, smodels = smodels)

    if mode != "cnf":
        # perform the cycle breaking
        logger.info("   Stats Original")
        logger.info("------------------------------------------------------------")
        program._decomposeGraph()
        logger.info(f"Tree Decomposition #bags: {program._td.bags} initial treewidth: {program._td.width} #vertices: {program._td.vertices}")
        logger.info("------------------------------------------------------------")
        if no_pp and write_name:
            with open(f'{write_name}.lp', mode='wb') as file_out:
                program.write_prog(file_out)
                exit(0)
        if cycle_breaking == "tp":
            program.tpUnfold()
        elif cycle_breaking == "binary":
            program.binary_cycle_breaking(local=False)
        elif cycle_breaking == "binary-opt":
            program.binary_cycle_breaking(local=True)
        elif cycle_breaking == "lt":
            program.less_than_cycle_breaking(opt=False)
        elif cycle_breaking == "lt-opt":
            program.less_than_cycle_breaking(opt=True)
        
        logger.info("   Cycle Breaking Done")
        logger.info("------------------------------------------------------------")
        if write_name:
            with open(f'{write_name}.lp', mode='wb') as file_out:
                program.write_prog(file_out, spanning=True)
        logger.info("   Stats After Cycle Breaking")
        logger.info("------------------------------------------------------------")
        if guide == "none":
            program.clark_completion()
        elif guide == "ors":
            program.td_guided_clark_completion()
        elif guide == "both":
            program.td_guided_both_clark_completion(adaptive=False, latest=False)
        elif guide == "adaptive":
            program.td_guided_both_clark_completion(adaptive=True, latest=True)
        elif guide == "choose":
            program.choose_clark_completion()
        logger.info("------------------------------------------------------------")

        cnf = program.get_cnf()
        if write_name:
            cnf.to_file(f'{write_name}.cnf', extras = True)
    if treewidth:
        logger.info("   Stats CNF")
        logger.info("------------------------------------------------------------")
        td = from_hypergraph(cnf.primal_hypergraph(), timeout = "-1")
        logger.info(f"Tree Decomposition #bags: {td.bags} CNF treewidth: {td.width} #vertices: {td.vertices}")      
        logger.debug(f"Evaluating CNF with {cnf.nr_vars} variables and {len(cnf.clauses)} clauses.")
        logger.info("------------------------------------------------------------")
    if not count:
        exit(0)

    # if mode == "mpeproblog" or mode == "optasp":
    #     weight, solution = cnf.solve_maxsat()
    #     weight = weight[0]
    #     assignment = ", ".join([ program._external_name(v) for v in program._guess if v in solution ])
    #     logger.result(f"The overall weight of the program is {weight}")# with {assignment}")
    #     return
    results = cnf.evaluate(strategy = strategy, preprocessing = preprocessing)

    # print the results
    logger.info("   Results")
    logger.info("------------------------------------------------------------")
    if mode != "cnf":
        queries = program.get_queries()
    else:
        queries = []
    if len(queries) > 0:
        for i,query in enumerate(queries):
            logger.result(f"{query}: {' '*max(1,(20 - len(query)))}{results[i]}")
    else:
        logger.result(f"The overall weight of the program is {results[0]}")

if __name__ == "__main__":
    main()


    
