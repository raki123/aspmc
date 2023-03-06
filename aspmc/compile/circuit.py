from operator import index
import queue
import numpy as np
import copy
import logging
import networkx as nx
from aspmc.util import *


logger = logging.getLogger("aspmc")

class Node(object):
    """A node class corresponding to nodes in a `Circuit`.
    
    Args:
        type (:obj:`int`): Which type the node has. One of `Node.AND, Node.OR, Node.NEG, Node.IN`.
        name (:obj:`int`): Unique identifier of the node.
        children (:obj:`iterable`, optional): The children of the node. Defaults to `[]`.
        ancestors (:obj:`iterable`, optional): The ancestors of the node. Defaults to `[]`.

    Attributes:
        type (:obj:`int`): Which type the node has. One of `Node.AND, Node.OR, Node.NEG, Node.IN`.
        name (:obj:`int`): Unique identifier of the node. 
        If `type` is `Node.NEG` or `Node.IN` this is the name of the (negated) input variable.
        children (:obj:`iterable`): The children of the node.
        ancestors (:obj:`iterable`): The ancestors of the node. 

    """
    AND = 0
    """Node type `AND` with value 0. Means that the children are conjoined."""
    OR = 1
    """Node type `OR` with value 1. Means that the children are disjoined."""
    NEG = 2
    """Node type `NEG` with value 2. Means that this is a negative input variable."""
    IN = 3
    """Node type `IN` with value 3. Means that this is a positive input variable."""
    def __init__(self, type, name, children = [], ancestors = []):
        self.type = type
        self.name = name
        self.children = children
        self.ancestors = ancestors

class Circuit(object):    
    """A circuit class that can store for example d-DNNFs and SDDs. 

    Offers methods to perform algebraic model counting on the circuit in linear time in the size of the (smooth) circuit.
    Also offers the same methods statically to avoid storing the circuit in memory. 
    Then the algebraic model counting is performed while reading the circuit.

    Supports the d-DNNF format of c2d and miniC2D for constructing circuits.
    
    Args:
        path (:obj:`string`): The path to the file that contains the circuit.

    Attributes:
        literals (:obj:`list`): The literals in the circuit. The node for literal `v` is in `literals[2*(v-1)]`, the one for `-v` is in `literals[2*(v-1)+1]`
        nodes (:obj:`list`): All the nodes of the circuit that are not literals.
    """
    def __init__(self, path):
        with open(path) as ddnnf:
            _, _, _, nr_leafs = ddnnf.readline().split()
            self.literals = []
            for var in range(1, int(nr_leafs) + 1):
                self.literals.append(Node(Node.IN, var))
                self.literals.append(Node(Node.NEG, -var))
            self.nodes = []
            idx = 0
            for line in ddnnf:
                line = line.strip().split()
                if line[0] == 'L':
                    node = self.literals[to_pos(int(line[1]))]
                    node.vars = (abs(int(line[1])),)
                elif line[0] == 'A':
                    node = Node(Node.AND, idx, children = [self.nodes[int(x)] for x in line[2:]])
                    node.vars = set()
                    for child in node.children:
                        child.ancestors.append(node)
                        node.vars.update(child.vars)
                    node.vars = tuple(node.vars)
                elif line[0] == 'O':
                    node = Node(Node.OR, idx, children = [self.nodes[int(x)] for x in line[3:]])
                    node.vars = set()
                    for child in node.children:
                        child.ancestors.append(node)
                        node.vars.update(child.vars)
                    node.vars = tuple(node.vars)
                self.nodes.append(node)
                idx += 1

    def non_smooth_wmc(self, weights):    
        """Performs weighted model counting over a circuit that is not smooth. Should be avoided since it is quite inefficient.
        
        Args:
            weights (:obj:`string`): The weights of the literals. 
                The weight for literal `v` is in `weights[2*(v-1)]`, the one for `-v` is in `weights[2*(v-1)+1]`

        Returns:
            (:obj:`object`): The weighted model count.
        """
        for i in range(len(self.literals)//2):
            self.literals[i*2].weight = weights[i*2]
            self.literals[i*2 + 1].weight = weights[i*2 + 1]

        todo = [ len(node.children) for node in self.nodes ]
        q = queue.Queue()
        for i in range(len(self.nodes)):
            if todo[i] == 0:
                q.put(self.nodes[i])
        while not q.empty():
            node = q.get()
            for anc in node.ancestors:
                todo[anc.name] -= 1
                if todo[anc.name] == 0:
                    q.put(anc)
            if node.type == Node.AND:
                value = np.full(len(weights[0]), 1.0)
                for child in node.children:
                    value *= child.weight
                node.weight = value
            elif node.type == Node.OR:
                value = np.full(len(weights[0]), 0.0)
                for child in node.children:
                    to_add = copy.deepcopy(child.weight)
                    for i in set(node.vars).difference(set(child.vars)):
                        to_add *= self.literals[to_pos(i)].weight + self.literals[neg(to_pos(i))].weight
                    value += to_add
                node.weight = value
        for i in set(range(1, 1 + len(self.literals)//2)).difference(set(node.vars)):
            node.weight *= self.literals[to_pos(i)].weight + self.literals[neg(to_pos(i))].weight
        return node.weight

    def wmc(self, weights):
        """Performs algebraic model counting over a circuit that is smooth.
        
        Args:
            weights (:obj:`string`): The weights of the literals. The weight for literal `v` is in `weights[2*(v-1)]`, the one for `-v` is in `weights[2*(v-1)+1]`

        Returns:
            (:obj:`object`): The algebraic model count.
        """
        for i in range(len(self.literals)//2):
            self.literals[i*2].weight = weights[i*2]
            self.literals[i*2 + 1].weight = weights[i*2 + 1]

        todo = [ len(node.children) for node in self.nodes ]
        q = queue.Queue()
        for i in range(len(self.nodes)):
            if todo[i] == 0:
                q.put(self.nodes[i])
        while not q.empty():
            node = q.get()
            for anc in node.ancestors:
                todo[anc.name] -= 1
                if todo[anc.name] == 0:
                    q.put(anc)
            if node.type == Node.AND:
                node.weight = np.full(len(weights[0]), 1.0)
                for child in node.children:
                    node.weight *= child.weight
            elif node.type == Node.OR:
                node.weight = np.full(len(weights[0]), 0.0)
                for child in node.children:
                    node.weight += child.weight
        return node.weight

    @staticmethod
    def parse_wmc(path, weights, zero = 0.0, one = 1.0, dtype = float, solver="c2d", vtree = None):
        """Performs algebraic model counting over a circuit that is smooth while parsing it.
        
        Args:
            path (:obj:`string`): The path to the file that contains the circuit.
            weights (:obj:`string`): The weights of the literals. The weight for literal `v` is in `weights[2*(v-1)]`, the one for `-v` is in `weights[2*(v-1)+1]`
            zero (:obj:`object`, optional): The neutral element of addition. Defaults to `0.0`.
            one (:obj:`object`, optional): The neutral element of multiplication. Defaults to `1.0`.
            dtype (:obj:`type`, optional): Which type the numpy arrays used to store the weights should have. Defaults to `float`.
            solver (:obj:`string`, optional): Which knowledge compiler this d-DNNF is from. Defaults to `c2d`.
            vtree (:obj:`aspmc.compile.vtree.Vtree`, optional): The underlying vtree if this is a non-smooth SDD. Defaults to `None`.
        Returns:
            (:obj:`object`): The algebraic model count.
        """
        if solver == "d4":
            return Circuit._parse_wmc_d4(path, weights, zero = zero, one = one, dtype = dtype)
        if solver == "miniC2D":
            return Circuit._parse_wmc_miniC2D(path, weights, zero = zero, one = one, dtype = dtype, vtree = vtree)
        shape = (np.shape(weights[0])[0], ) + np.shape(one)
        with open(path) as ddnnf:
            _, v, e, n = ddnnf.readline().split()
            logger.debug(f"d-DNNF size: {v} nodes, {e} edges, {n} variables")
            mem = [] # np.empty((int(v), ) + shape, dtype=dtype) (this seems to perform worse than using mem.append() in a loop !?)
            idx = 0
            for line in ddnnf:
                line = line.strip().split()
                mem.append(np.empty(shape, dtype = dtype))
                if line[0] == 'L':
                    mem[idx][:] = weights[to_pos(int(line[1]))]
                elif line[0] == 'A':
                    mem[idx][:] = one
                    for x in line[2:]:
                        mem[idx] *= mem[int(x)]
                elif line[0] == 'O':
                    mem[idx][:] = zero
                    for x in line[3:]:
                        mem[idx] += mem[int(x)]
                idx += 1
            return mem[idx - 1]

    @staticmethod
    def live_parse_wmc(pipe, weights, zero = 0.0, one = 1.0, dtype = float):
        """Performs algebraic model counting over a circuit that is smooth while parsing it.
        
        Args:
            pipe (:obj:`stream`): The pipe where the circuit is printed.
            weights (:obj:`string`): The weights of the literals. The weight for literal `v` is in `weights[2*(v-1)]`, the one for `-v` is in `weights[2*(v-1)+1]`
            zero (:obj:`object`, optional): The neutral element of addition. Defaults to `0.0`.
            one (:obj:`object`, optional): The neutral element of multiplication. Defaults to `1.0`.
            dtype (:obj:`type`, optional): Which type the numpy arrays used to store the weights should have. Defaults to `float`.
        Returns:
            (:obj:`object`): The algebraic model count.
        """
        mem = [] 
        shape = (np.shape(weights[0])[0], ) + np.shape(one)
        idx = 0
        for line in pipe:
            line = line.decode().strip().split()
            if line[0] == 'c':
                continue
            mem.append(np.empty(shape, dtype = dtype))
            if line[0] == 'L':
                mem[idx][:] = weights[to_pos(int(line[1]))]
            elif line[0] == 'A':
                mem[idx][:] = one
                for x in line[2:]:
                    mem[idx] *= mem[int(x)]
            elif line[0] == 'O':
                mem[idx][:] = zero
                for x in line[3:]:
                    mem[idx] += mem[int(x)]
            idx += 1
        return mem[idx - 1]

    @staticmethod
    def _parse_wmc_d4(path, weights, zero = 0.0, one = 1.0, dtype = float):
        shape = (np.shape(weights[0])[0], ) + np.shape(one)
        with open(path) as ddnnf:
            mem = [ None ] # the values of the nodes
            mem_type = [ False ] # whether the nodes are multiplicative
            for line in ddnnf:
                line = line.strip().split()
                if line[0] == 't': # add a true node
                    mem.append(np.full(shape, one, dtype=dtype))
                    mem_type.append(True)
                elif line[0] == 'f': # add a false node
                    mem.append(np.full(shape, zero, dtype=dtype))
                    mem_type.append(False)
                elif line[0] == 'a': # add an and node
                    mem.append(np.full(shape, one, dtype=dtype))
                    mem_type.append(True)
                elif line[0] == 'o': # add an or node
                    mem.append(np.full(shape, zero, dtype=dtype))
                    mem_type.append(False)
                elif mem_type[int(line[0])]: # add edge of an and node
                    mem[int(line[0])] *= mem[int(line[1])]
                else: # add edge of an or node                    
                    val = copy.deepcopy(mem[int(line[1])])
                    idx = 2
                    lit = int(line[idx])
                    while lit != 0:
                        val *= weights[to_pos(lit)]
                        idx += 1
                        lit = int(line[idx])
                    idx += 1
                    var = int(line[idx])
                    while var != 0:
                        val *= weights[to_pos(var)] + weights[neg(to_pos(var))]
                        idx += 1
                        var = int(line[idx])
                    mem[int(line[0])] += val
            return mem[1]

    @staticmethod
    def _parse_wmc_miniC2D(path, weights, zero = 0.0, one = 1.0, dtype = float, vtree = None):
        # setup phase: 
        # get the least common ancestors to speed up queries
        vtree_graph = vtree.to_networkx()
        vtree.index()
        lca = [ [ -1 for _ in range(vtree.leaf_count()*2) ] for _ in range(vtree.leaf_count()*2) ]
        for p,l in nx.tree_all_pairs_lowest_common_ancestor(vtree_graph):
            lca[p[1]][p[0]] = l
            lca[p[0]][p[1]] = l

        shape = (np.shape(weights[0])[0], ) + np.shape(one)

        index_to_node = { node.idx : node for node in vtree }
        index_to_node = [ index_to_node[i] for i in range(1, vtree.leaf_count()*2) ]
        # method to get the weight of the free variables not included in the SDD between node i and j
        def factor(i, j):
            res = np.full(shape, one, dtype=dtype)
            if lca[i][j] == j: # i should always be above j
                i,j = j,i
            if i == j:
                return res
            upper = index_to_node[i - 1]
            lower = index_to_node[j - 1]
            stack = queue.LifoQueue()
            cur = upper
            down = True
            while cur != upper or down:
                if down:
                    if cur == lower:
                        down = False
                    elif cur.val is None:
                        stack.put(cur)
                        cur = cur.left
                    else:
                        res *= weights[to_pos(cur.val)] + weights[neg(to_pos(cur.val))]
                        down = False
                else:
                    last = cur
                    cur = stack.get()
                    if cur.left == last:
                        stack.put(cur)
                        cur = cur.right
                        down = True
            return res

        # the actual counting phase
        with open(path) as ddnnf:
            _, v, e, n = ddnnf.readline().split()
            logger.debug(f"d-DNNF size: {v} nodes, {e} edges, {n} variables")
            mem = []
            vtree_nodes = []
            idx = 0
            for line in ddnnf:
                line = line.strip().split()
                if line[0] == 'L':
                    val = weights[to_pos(int(line[1]))]
                    vtree_node = abs(int(line[1]))
                else:
                    if line[0] == 'A':
                        vtree_node = lca[vtree_nodes[int(line[2])]][vtree_nodes[int(line[3])]]
                        left = index_to_node[vtree_node-1].left.idx
                        right = index_to_node[vtree_node-1].right.idx
                        if lca[right][vtree_nodes[int(line[2])]] != right:
                            right, left = left, right
                        val = mem[int(line[2])]*factor(right, vtree_nodes[int(line[2])])*mem[int(line[3])]*factor(left, vtree_nodes[int(line[3])])
                    elif line[0] == 'O':
                        vtree_node = lca[vtree_nodes[int(line[3])]][vtree_nodes[int(line[4])]]  
                        for x in line[3:]:
                            vtree_node = lca[vtree_node][vtree_nodes[int(x)]]         
                        val = np.full(shape, zero, dtype=dtype)
                        for x in line[3:]:
                            val += mem[int(x)]*factor(vtree_node, vtree_nodes[int(x)])
                mem.append(val)
                vtree_nodes.append(vtree_node)
                idx += 1
            mem[idx - 1] *= factor(vtree_node, vtree.idx)
            return mem[idx - 1]
