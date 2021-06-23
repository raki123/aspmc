#!/home/hecher/miniconda3/bin/python3
##/usr/bin/env python3

"""
Main module providing the application logic.
"""

import matplotlib.pyplot as plt
import numpy as np
import sys
import networkx as nx
import os
import inspect
import logging
import subprocess
import math
import queue
import time
import importlib
# set library path
#start = time.time()
# TODO: fixme
src_path = os.path.abspath(os.path.realpath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, os.path.realpath(os.path.join(src_path, '../..')))

src_path = os.path.realpath(os.path.join(src_path, '../../lib'))

libs = ['htd_validate', 'clingoparser', 'nesthdb', 'htd', 'c2d']

if src_path not in sys.path:
    for lib in libs:
        sys.path.insert(0, os.path.join(src_path, lib))


logger = logging.getLogger("asp2sat")
logging.basicConfig(format='[%(levelname)s] %(name)s: %(message)s', level="INFO")

from htd_validate.utils import hypergraph, graph

import clingoext
from clingoext import ClingoRule
from dpdb import reader
from dpdb import treedecomp
from dpdb.problems.sat_util import *
from dpdb.writer import StreamWriter
import tempfile

import wfParse
import backdoor
import stats
import grounder
from parser import ProblogParser
from semantics import ProblogSemantics


class Rule(object):
    def __init__(self, head, body):
        self.head = head
        self.body = body

    def __repr__(self):
        return "; ".join([str(a) for a in self.head]) + ":- " + ", ".join([ ("not " if b < 0 else "") + str(abs(b)) for b in self.body]) 

class Semiring(object):
    pass

class Program(object):
    def __init__(self, clingo_control):
        # the variable counter
        self._max = 0
        self._nameMap = {}
        # store the clauses here
        self._clauses = []
        # remember which variables are guesses and which are derived
        self._guess = set()
        self._deriv = set()
        self._copies = {}
        self._normalize(clingo_control)
        #for r in self._program:
        #    print("; ".join([self._nameMap[a] for a in r.head]) + ":- " + ", ".join([ ("not " if b < 0 else "") + self._nameMap[abs(b)] for b in r.body]))

    def remove_tautologies(self, clingo_control):
        tmp = []
        for o in clingo_control.ground_program.objects:
            if isinstance(o, ClingoRule) and set(o.head).intersection(set(o.body)) == set():
                tmp.append(o)
        return tmp

    def _normalize(self, clingo_control):
        program = self.remove_tautologies(clingo_control)
        self._program = []
        _atomToVertex = {} # htd wants succinct numbering of vertices / no holes
        _vertexToAtom = {} # inverse mapping of _atomToVertex 
        unary = []

        symbol_map = {}
        for sym in clingo_control.symbolic_atoms:
            symbol_map[sym.literal] = str(sym.symbol)
        for o in program:
            if isinstance(o, ClingoRule):
                o.atoms = set(o.head)
                o.atoms.update(tuple(map(abs, o.body)))
                if len(o.body) > 0:
                    self._program.append(o)
                    for a in o.atoms.difference(_atomToVertex):	# add mapping for atom not yet mapped
                        if a in symbol_map:
                            _atomToVertex[a] = self.new_var(symbol_map[a])
                        else:
                            _atomToVertex[a] = self.new_var(f"projected_away({a})")
                        _vertexToAtom[self._max] = a
                else:
                    if o.choice:
                        unary.append(o)
        for o in unary:
            self._program.append(o)
            for a in o.atoms.difference(_atomToVertex):	# add mapping for atom not yet mapped
                _atomToVertex[a] = self.new_var(symbol_map[a])
                _vertexToAtom[self._max] = a

        trans_prog = set()
        for r in self._program:
            if r.choice: 
                self._guess.add(_atomToVertex[r.head[0]])
            else:
                head = list(map(lambda x: _atomToVertex[x], r.head))
                body = list(map(lambda x: _atomToVertex[abs(x)]*(1 if x > 0 else -1), r.body))
                trans_prog.add(Rule(head,body))
        self._program = trans_prog
        self._deriv = set(range(1,self._max + 1)).difference(self._guess)

    def primalGraph(self):
        return self._graph

    def new_var(self, name):
        self._max += 1
        self._nameMap[self._max] = name if name != "" else str(self._max)
        return self._max

    def copy_var(self, var):
        if "(" in self._nameMap[var]:
            idx = self._nameMap[var].index("(")
            inputs = self._nameMap[var][idx:]
        else:
            inputs = ""
        if "_copy_" in self._nameMap[var]:
            idx = self._nameMap[var].index("_copy_")
            pred = self._nameMap[var][:idx]
        else:
            pred = self._nameMap[var]
            if "(" in pred:
                idx = pred.index("(")
                pred = pred[:idx]
            if pred+inputs not in self._copies:
                self._copies[pred+inputs] = [var]
        cnt = len(self._copies[pred+inputs])
        name = pred + "_copy_" + str(cnt) + inputs
        nv = self.new_var(name)
        self._copies[pred+inputs].append(nv)
        return nv

    def _computeComponents(self):
        self.dep = nx.DiGraph()
        for r in self._program:
            for a in r.head:
                for b in r.body:
                    if b > 0:
                        self.dep.add_edge(b, a)
        comp = nx.algorithms.strongly_connected_components(self.dep)
        self._components = list(comp)
        self._condensation = nx.algorithms.condensation(self.dep, self._components)

    def treeprocess(self):
        ins = {}
        outs = {}
        for a in self._deriv.union(self._guess):
            ins[a] = set()
            outs[a] = set()
        for r in self._program:
            for a in r.head:
                ins[a].add(r)
            for b in r.body:
                if b > 0:
                    outs[b].add(r)
        ts = nx.topological_sort(self._condensation)
        ancs = {}
        decs = {}
        for t in ts:
            comp = self._condensation.nodes[t]["members"]
            for v in comp:
                ancs[v] = set([vp[0] for vp in self.dep.in_edges(nbunch=v) if vp[0] in comp])
                decs[v] = set([vp[1] for vp in self.dep.out_edges(nbunch=v) if vp[1] in comp])
        q = set([v for v in ancs.keys() if len(ancs[v]) == 1 and len(decs[v]) == 1 and list(ancs[v])[0] == list(decs[v])[0]])
        while not len(q) == 0:
            old_v = q.pop()
            if len(ancs[old_v]) == 0:
                continue
            new_v = self.copy_var(old_v)
            self._deriv.add(new_v)
            ins[new_v] = set()
            outs[new_v] = set()
            anc = ancs[old_v].pop()
            ancs[anc].remove(old_v)
            decs[anc].remove(old_v)
            if len(ancs[anc]) == 1 and len(decs[anc]) == 1 and list(ancs[anc])[0] == list(decs[anc])[0]:
                q.add(anc)

            # this contains all rules that do not use anc to derive v
            to_rem = ins[old_v].difference(outs[anc])
            # this contains all rules that use anc to derive v
            # we just keep them as they are
            ins[old_v] = ins[old_v].intersection(outs[anc])
            # any rule that does not use anc to derive v can now only derive new_v
            for r in to_rem:
                head = [b if b != old_v else new_v for b in r.head]
                new_r = Rule(head,r.body)
                ins[new_v].add(new_r)
                for b in r.body:
                    if b > 0:
                        outs[b].remove(r)
                        outs[b].add(new_r)

            # this contains all rules that use v and derive anc
            to_rem = outs[old_v].intersection(ins[anc])
            # this contains all rules that use v and do not derive anc
            # we just keep them as they are
            outs[old_v] = outs[old_v].difference(ins[anc])
            # any rule that uses v to derive anc must use new_v
            for r in to_rem:
                body = [ (b if b != old_v else new_v) for b in r.body]
                new_r = Rule(r.head,body)
                for b in r.head:
                    ins[b].remove(r)
                    ins[b].add(new_r)
                for b in r.body:
                    if b > 0:
                        if b != old_v:
                            outs[abs(b)].remove(r)
                            outs[abs(b)].add(new_r)
                        else:
                            outs[new_v].add(new_r)
            new_r = Rule([old_v], [new_v])
            ins[old_v].add(new_r)
            outs[new_v].add(new_r)
        # only keep the constraints
        self._program = [r for r in self._program if len(r.head) == 0]
        # add all the other rules
        for a in ins.keys():
            self._program.extend(ins[a])


    def write_scc(self, comp):
        res = ""
        for v in comp:
            res += f"p({v}).\n"
            ancs = set([vp[0] for vp in self.dep.in_edges(nbunch=v) if vp[0] in comp])
            for vp in ancs:
                res += f"edge({vp},{v}).\n"
        return res

    def compute_backdoor(self, idx):
        comp = self._condensation.nodes[idx]["members"]
        local_dep = self.dep.subgraph(comp)
        try:
            if len(comp) > 100:
                basis = nx.cycle_basis(local_dep.to_undirected())
                res = []
                while len(basis) > 0:
                    prog = f"b({len(comp)//2}).\n" + "\n".join([f"p({v})." for v in comp if v not in res]) + "\n"
                    for c in basis:
                        prog += ":-" + ", ".join([f"not abs({v})" for v in c]) + ".\n"
                    c = backdoor.ClingoControl(prog)
                    res += c.get_backdoor(os.path.dirname(os.path.abspath(__file__)) + "/guess_backdoor.lp")[2][0]
                    local_dep = self.dep.subgraph([x for x in comp if x not in res])
                    basis = nx.cycle_basis(local_dep.to_undirected())
            else:
                try:
                    c = backdoor.ClingoControl(f"b({len(comp)//2}).\n" + self.write_scc(comp))
                    res = c.get_backdoor(os.path.dirname(os.path.abspath(__file__)) + "/guess_tree.lp")[2][0]
                except:
                    basis = nx.cycle_basis(local_dep.to_undirected())
                    res = []
                    while len(basis) > 0:
                        prog = "\n".join([f"p({v})." for v in comp if v not in res]) + "\n"
                        for c in basis:
                            prog += ":-" + ", ".join([f"not abs({v})" for v in c]) + ".\n"
                        c = backdoor.ClingoControl(prog)
                        res += c.get_backdoor(os.path.dirname(os.path.abspath(__file__)) + "/guess_backdoor.lp")[2][0]
                        local_dep = self.dep.subgraph([x for x in comp if x not in res])
                        basis = nx.cycle_basis(local_dep.to_undirected())
        except:
            res = comp
            logger.error("backdoor guessing failed, returning whole component.")
        print("backdoor comp: " + str(len(comp)))
        print("backdoor res: " + str(len(res)))
        return res

    def backdoor_process(self, comp, backdoor):
        comp = set(comp)
        backdoor = set(backdoor)

        toRemove = set()
        ins = {}
        for a in comp:
            ins[a] = set()
        for r in self._program:
            for a in r.head:
                if a in comp:
                    ins[a].add(r)
                    toRemove.add(r)

        copies = {}
        for a in comp:
            copies[a] = {}
            copies[a][len(backdoor)] = a

        def getAtom(atom, i):
            # negated atoms are kept as they are
            if atom < 0:
                return atom
            # atoms that are not from this component are input atoms and should stay the same
            if atom not in comp:
                return atom
            if i < 0:
                print("this should not happen")
                exit(-1)
            if atom not in copies:
                print("this should not happen")
                exit(-1)
            if i not in copies[atom]:
                copies[atom][i] = self.copy_var(atom)
                self._deriv.add(copies[atom][i])
            return copies[atom][i]

        toAdd = set()
        for a in backdoor:
            for i in range(1,len(backdoor)+1):
                head = [getAtom(a, i)]
                for r in ins[a]:
                    if i == 1:
                        # in the first iteration we do not add rules that use atoms from the backdoor
                        add = True
                        for x in r.body:
                            if x > 0 and x in backdoor:
                                add = False
                    else:
                        # in all but the first iteration we only use rules that use at least one atom from the SCC we are in
                        add = False
                        for x in r.body:
                            if x > 0 and x in comp:
                                add = True
                    if add:
                        body = [getAtom(x, i - 1) for x in r.body]
                        new_rule = Rule(head, body)
                        toAdd.add(new_rule)
                if i > 1:
                    toAdd.add(Rule(head, [getAtom(a, i - 1)]))

        for a in comp.difference(backdoor):
            for i in range(len(backdoor)+1):
                head = [getAtom(a, i)]
                for r in ins[a]:
                    if i == 0:
                        # in the first iteration we only add rules that only use atoms from outside 
                        add = True
                        for x in r.body:
                            if x > 0 and x in backdoor:
                                add = False
                    else:
                        # in all other iterations we only use rules that use at least one atom from the SCC we are in
                        add = False
                        for x in r.body:
                            if x >  0 and x in comp:
                                add = True
                    if add:
                        body = [getAtom(x, i) for x in r.body]
                        new_rule = Rule(head, body)
                        toAdd.add(new_rule)
                if i > 0:
                    toAdd.add(Rule(head, [getAtom(a, i - 1)]))

        #print(toAdd)
        self._program = [r for r in self._program if r not in toRemove]
        self._program += list(toAdd)
        
        
    def preprocess(self):
        self._computeComponents()
        self.treeprocess()
        self._computeComponents()
        ts = nx.topological_sort(self._condensation)
        for t in ts:
            comp = self._condensation.nodes[t]["members"]
            if len(comp) > 1:
                self.backdoor_process(comp, self.compute_backdoor(t))
        self._computeComponents()
        self.treeprocess()
        self._computeComponents()
        ts = nx.topological_sort(self._condensation)
        for t in ts:
            comp = self._condensation.nodes[t]["members"]
            if len(comp) > 1:
                print("this should not happen")
                exit(-1)

    def clark_completion(self):
        perAtom = {}
        for a in self._deriv:
            perAtom[a] = []

        for r in self._program:
            for a in r.head:
                perAtom[a].append(r)

        for head in self._deriv:
            ors = []
            for r in perAtom[head]:
                ors.append(self.new_var(f"{r}"))
                ands = [-x for x in r.body]
                self._clauses.append([ors[-1]] + ands)
                for at in ands:
                    self._clauses.append([-ors[-1], -at])
            self._clauses.append([-head] + [o for o in ors])
            for o in ors:
                self._clauses.append([head, -o])

        constraints = [r for r in self._program if len(r.head) == 0]
        for r in constraints:
            self._clauses.append([-x for x in r.body])

    def _generatePrimalGraph(self):
        self._graph = hypergraph.Hypergraph()
        for r in self._program:
            atoms = set(r.head)
            atoms.update(tuple(map(abs, r.body)))
            self._graph.add_hyperedge(tuple(atoms), checkSubsumes = not self.no_sub)

    def _decomposeGraph(self):
        # Run htd
        p = subprocess.Popen([os.path.join(src_path, "htd/bin/htd_main"), "--seed", "12342134", "--input", "hgr", "--child-limit", "2"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self._graph.write_graph(p.stdin, dimacs=False, non_dimacs="tw", print_id = False)
        p.stdin.close()
        tdr = reader.TdReader.from_stream(p.stdout)
        p.wait()
        self._td = treedecomp.TreeDecomp(tdr.num_bags, tdr.tree_width, tdr.num_orig_vertices, tdr.root, tdr.bags, tdr.adjacency_list, None)
        logger.info(f"Tree decomposition #bags: {self._td.num_bags} tree_width: {self._td.tree_width} #vertices: {self._td.num_orig_vertices} #leafs: {len(self._td.leafs)} #edges: {len(self._td.edges)}")

    def td_guided_clark_completion(self):
        self._generatePrimalGraph()
        self._decomposeGraph()

        # at which td node to handle each rule
        rules = {}
        # at which td node each variable occurs first
        last = {}
        tree = nx.DiGraph()
        tree.add_nodes_from(range(len(self._td.nodes)))
        idx = 0
        td_idx = self._td.nodes
        for t in self._td.nodes:
            for a in t.vertices:
                last[a] = idx
            t.idx = idx
            for tp in t.children:
                tree.add_edge(t.idx, tp.idx)
            idx += 1
            rules[t] = []

        for r in self._program:
            for a in r.head:
                r.proven = self.new_var(f"{r}")
                ands = [-x for x in r.body]
                self._clauses.append([r.proven] + ands)
                for at in ands:
                    self._clauses.append([-r.proven, -at])
            idx = min([last[abs(b)] for b in r.body + r.head])
            rules[td_idx[idx]].append(r)

        # how many rules have we used and what is the last used variable
        unfinished = {}
        # first td pass: determine rules and prove_atoms
        for t in self._td.nodes:
            unfinished[t] = {}
            t.vertices = set(t.vertices)
            to_handle = {}
            for a in t.vertices:
                to_handle[a] = []
            for tp in t.children:
                removed = tp.vertices.difference(t.vertices)
                for a in removed:
                    if a in self._deriv:
                        if a in unfinished[tp]:
                            final = unfinished[tp].pop(a)
                            self._clauses.append([-a, final])
                            self._clauses.append([a, -final])
                        else: 
                            self._clauses.append([-a])
                rest = tp.vertices.intersection(t.vertices)
                for a in rest:
                    if a in unfinished[tp]:
                        to_handle[a].append(unfinished[tp][a])
            # take the rules we need and remove them
            for r in rules[t]:
                for a in r.head:
                    to_handle[a].append(r.proven)

            # handle all the atoms we have gathered
            for a in t.vertices:
                if len(to_handle[a]) > 1:
                    new_last = self.new_var("{t},{a}")
                    self._clauses.append([-new_last] + to_handle[a])
                    for at in to_handle[a]:
                        self._clauses.append([new_last, -at])
                    unfinished[t][a] = new_last
                elif len(to_handle[a]) == 1:
                    unfinished[t][a] = to_handle[a][0]

        for a in self._td.root.vertices:
            if a in self._deriv:
                if a in unfinished[self._td.root]:
                    final = unfinished[self._td.root].pop(a)
                    self._clauses.append([-a, final])
                    self._clauses.append([a, -final])
                else: 
                    self._clauses.append([-a])

        constraints = [r for r in self._program if len(r.head) == 0]
        for r in constraints:
            self._clauses.append([-x for x in r.body])

    def write_dimacs(self, stream, debug = False):
        stream.write(f"p cnf {self._max} {len(self._clauses)}\n".encode())
        if debug:
            for c in self._clauses:
                stream.write((" ".join([("not " if v < 0 else "") + self._nameMap[abs(v)] for v in c]) + " 0\n" ).encode())
        else:
            for c in self._clauses:
                stream.write((" ".join([str(v) for v in c]) + " 0\n" ).encode())

    def prog_string(self, program, problog=False):
        result = ""
        for v in self._guess:
            if problog:
                result += f"0.5::{self._nameMap[v]}.\n"
            else:
                result += f"{{{self._nameMap[v]}}}.\n"
        for r in program:
            result += ";".join([self._nameMap[v] for v in r.head])
            result += ":-"
            result += ",".join([("not " if v < 0 else "") + self._nameMap[abs(v)] for v in r.body])
            result += ".\n"
        if problog:
            result += "query(smokes(X))."
        return result

    def write_prog(self, stream):
        stream.write(self.prog_string(self._program, False).encode())

    def encoding_stats(self):
        num_vars, edges= cnf2primal(self._max, self._clauses)
        p = subprocess.Popen([os.path.join(src_path, "htd/bin/htd_main"), "--seed", "12342134", "--input", "hgr"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        logger.debug("Running htd")
        StreamWriter(p.stdin).write_gr(num_vars, edges)
        p.stdin.close()
        tdr = reader.TdReader.from_stream(p.stdout)
        p.wait()
        logger.debug("Parsing tree decomposition")
        td = treedecomp.TreeDecomp(tdr.num_bags, tdr.tree_width, tdr.num_orig_vertices, tdr.root, tdr.bags, tdr.adjacency_list, None)
        logger.info(f"Tree decomposition #bags: {td.num_bags} tree_width: {td.tree_width} #vertices: {td.num_orig_vertices} #leafs: {len(td.leafs)} #edges: {len(td.edges)}")
            
if __name__ == "__main__":
    control = clingoext.Control()
    mode = sys.argv[1]
    weights = {}
    no_sub = False
    no_pp = False
    if len(sys.argv) > 2 and sys.argv[2] == "-no_subset_check":
        logger.info("   Not performing subset check when adding edges to hypergraph.")
        no_sub = True
        del sys.argv[2]
    elif len(sys.argv) > 2 and sys.argv[2] == "-no_pp":
        logger.info("   No Preprocessin")
        no_pp = True
        del sys.argv[2]
    if len(sys.argv) > 2 and sys.argv[2] == "-semiring":
        logger.info(f"   Using semiring {sys.argv[3]}.")
        sr = sys.argv[3]
        semiring = importlib.import_module(sr)
        del sys.argv[2]
        del sys.argv[2]
    else:
        semiring = Semiring()
        def float_parse(f, atom = None):
            return float(f)
        semiring.parse = float_parse
        semiring.one = 1.0
        semiring.zero = 0.0
        semiring.negate = lambda x : 1.0 - x
        semiring.dtype = float
    if mode == "asp":
        program_files = sys.argv[2:]
        program_str = None
        if not program_files:
            program_str = sys.stdin.read()
    elif mode.startswith("problog"):
        files = sys.argv[2:]
        program_str = ""
        if not files:
            program_str = sys.stdin.read()
        for path in files:
            with open(path) as file_:
                program_str += file_.read()
        parser = ProblogParser()
        program = parser.parse(program_str, semantics = ProblogSemantics())

        queries = [ r for r in program if r.is_query() ]
        program = [ r for r in program if not r.is_query() ]

        for r in program:
            if r.weight is not None:
                weights[str(r.head)] = semiring.parse(r.weight, atom = r.head)

        program_str = "".join([ r.asp_string() for r in program])
        program_files = []
    grounder.ground(control, program_str = program_str, program_files = program_files)
    program = Program(control)
    program.no_sub = no_sub

    logger.info("   Stats Original")
    logger.info("------------------------------------------------------------")
    program._generatePrimalGraph()
    program._decomposeGraph()
    logger.info("------------------------------------------------------------")

    if no_pp:
        with open('out.lp', mode='wb') as file_out:
            program.write_prog(file_out)
            exit(0)

    program.preprocess()
    logger.info("   Preprocessing Done")
    logger.info("------------------------------------------------------------")
    
    with open('out.lp', mode='wb') as file_out:
        program.write_prog(file_out)
    #program.clark_completion()
    logger.info("   Stats translation")
    logger.info("------------------------------------------------------------")
    program.td_guided_clark_completion()
    logger.info("------------------------------------------------------------")

    with open('out.cnf', mode='wb') as file_out:
        program.write_dimacs(file_out)

    #logger.info("   Stats CNF")
    #logger.info("------------------------------------------------------------")
    #program.encoding_stats()
    if mode != "problogwmc":
        exit(0)
    logger.info("------------------------------------------------------------")
    p = subprocess.Popen([os.path.join(src_path, "c2d/bin/c2d_linux"), "-smooth_all", "-reduce", "-in", "out.cnf"], stdout=subprocess.PIPE)
    p.wait()
    import circuit
    if mode == "asp":
        weight_list = [ np.array([1.0]) for _ in range(program._max*2) ]
    elif mode.startswith("problog"):
        query_cnt = len(queries)
        varMap = { name : var for  var, name in program._nameMap.items() }
        weight_list = [ np.full(query_cnt, semiring.one, dtype=semiring.dtype) for _ in range(program._max*2) ]
        for name in weights:
            weight_list[(varMap[name]-1)*2] = np.full(query_cnt, weights[name], dtype=semiring.dtype)
            weight_list[(varMap[name]-1)*2 + 1] = np.full(query_cnt, semiring.negate(weights[name]), dtype=semiring.dtype)
        for i, query in enumerate(queries):
            atom = str(query.atom)
            weight_list[(varMap[atom]-1)*2 + 1][i] = semiring.zero
    logger.info("   Results")
    logger.info("------------------------------------------------------------")
    results = circuit.Circuit.parse_wmc("out.cnf.nnf", weight_list, zero = semiring.zero, one = semiring.one, dtype = semiring.dtype)
    
    if mode == "asp":
        logger.info(f"The program has {int(results[0])} models")
    elif mode.startswith("problog"):
        for i, query in enumerate(queries):
            atom = str(query.atom)
            logger.info(f"{atom}: {' '*max(1,(20 - len(atom)))}{results[i]}")
