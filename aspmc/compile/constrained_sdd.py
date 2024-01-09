import queue
from aspmc.util import *
import networkx as nx
import numpy as np

class Node(object):    
    """A node class corresponding to nodes in a `ConstrainedSDD`.
    
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
        vtree_node (:obj:`int`): The lowest vtree node that this node respects.

    """
    AND = 0
    """Node type `AND` with value 0. Means that the children are conjoined."""
    OR = 1
    """Node type `OR` with value 1. Means that the children are disjoined."""
    NEG = 2
    """Node type `NEG` with value 2. Means that this is a negative input variable."""
    IN = 3
    """Node type `IN` with value 3. Means that this is a positive input variable."""
    AND = 0
    OR = 1
    NEG = 2
    IN = 3
    def __init__(self, type, name, children = [], ancestors = []):
        self.type = type
        self.name = name
        self.vtree_node = None
        if self.type == Node.IN or self.type == Node.NEG:
            self.vtree_node = abs(name)
        self.children = children
        self.ancestors = ancestors

class ConstrainedSDD(object):    
    """A circuit class that can store SDDs. 

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
    def __init__(self, path = None, v3 = None):
        if v3 != None:
            self.set_vtree(v3)
        if path != None:
            with open(path) as ddnnf:
                _, nr_nodes, nr_edges, nr_leafs = ddnnf.readline().split()
                self.literals = []
                for var in range(1, int(nr_leafs) + 1):
                    self.literals.append(Node(Node.IN, var))
                    self.literals.append(Node(Node.NEG, -var))
                self.nodes = []
                idx = 0
                for line in ddnnf:
                    line = line.strip().split()
                    if line[0] == 'L':
                        node = self.literals[2*(abs(int(line[1]))-1) + (1 if int(line[1]) < 0 else 0)]
                    elif line[0] == 'A':
                        node = Node(Node.AND, idx, children = [self.nodes[int(x)] for x in line[2:]])
                        for child in node.children:
                            child.ancestors.append(node)
                    elif line[0] == 'O':
                        node = Node(Node.OR, idx, children = [self.nodes[int(x)] for x in line[3:]])
                        for child in node.children:
                            child.ancestors.append(node)
                    self.nodes.append(node)
                    idx += 1

    def set_vtree(self, v3):
        self.vtree = v3
        self.vtree_graph = self.vtree.to_networkx()
        self.vtree.index()
        self.lca = [ [ -1 for _ in range(self.vtree.leaf_count()*2) ] for _ in range(self.vtree.leaf_count()*2) ]
        for p,l in nx.tree_all_pairs_lowest_common_ancestor(self.vtree_graph):
            self.lca[p[1]][p[0]] = l
            self.lca[p[0]][p[1]] = l


    def get_vtree_node(self, node):
        if node.vtree_node is None:
            node.vtree_node = self.lca[(node.children[0].vtree_node, node.children[1].vtree_node)]
        return node.vtree_node
        
    def separator_node(self, P):
        stack = queue.LifoQueue()
        cur = self.vtree
        down = True
        lefts = 0
        seen = set()
        while not (lefts == 0 and seen.issuperset(P)):
            if down:
                if cur.val is None:
                    stack.put(cur)
                    cur = cur.left
                    lefts += 1
                else:
                    seen.add(cur.val)
                    down = False
            else:
                last = cur
                cur = stack.get()
                if last == cur.left:
                    stack.put(cur)
                    cur = cur.right
                    lefts -= 1
                    down = True
        return cur.idx

    def wmc(self, weights, P, first_semiring, second_semiring, transform):        
        """Performs (two) algebraic model counting over the X/D-constrained SDD.
        
        Args:
            weights (:obj:`string`): The weights of the literals. The weight for literal `v` is in `weights[2*(v-1)]`, the one for `-v` is in `weights[2*(v-1)+1]`
            P (:obj:`iterable`): The set of variables that are quantified over the first semiring.
            first_semiring (:obj:`module`): The module of the first semiring.
            second_semiring (:obj:`module`): The module of the second semiring.
            transform (:obj:`string`): The transformation function used to transform a value from the second semiring into a value from the first semiring.
                Will be used as

                        f_transform = eval(transform)
                        transform = lambda x : first_semiring.from_value(f_transform(x))
        Returns:
            (:obj:`object`): The algebraic model count.
        """
        first_shape = (np.shape(weights[0])[0], ) + np.shape(first_semiring.one())
        second_shape = (np.shape(weights[0])[0], ) + np.shape(second_semiring.one())

        # initialize the transform function
        f_transform = eval(transform)
        transform = lambda x : first_semiring.from_value(f_transform(x))

        separator_node = self.separator_node(P)
        for i in range(len(self.literals)):
            if abs(to_dimacs(i)) in P:
                self.literals[i].weight = weights[i]
            elif self.lca[separator_node][abs(to_dimacs(i))] == separator_node: 
                self.literals[i].weight = weights[i]
            else:
                self.literals[i].weight = np.array([ transform(w) for w in weights[i] ])

        
        index_to_node = { node.idx : node for node in self.vtree.nodes() }
        index_to_node = [ index_to_node[i] for i in range(1, self.vtree.leaf_count()*2) ]
        def factor(i, j):
            if self.lca[i][j] == j: # i should always be above j
                i,j = j,i
            if self.lca[i][separator_node] == separator_node and i not in P:
                res = np.full(second_shape, second_semiring.one())
            else:
                res = np.full(first_shape, first_semiring.one())
            if i == j:
                return res
            upper = index_to_node[i - 1]
            lower = index_to_node[j - 1]
            res = np.full(first_shape, first_semiring.one())
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
                        res *= self.literals[to_pos(cur.val)].weight + self.literals[neg(to_pos(cur.val))].weight
                        down = False
                else:
                    last = cur
                    cur = stack.get()
                    if cur.left == last:
                        stack.put(cur)
                        cur = cur.right
                        down = True
            return res

        todo = [ len(node.children) for node in self.nodes ]
        q = queue.Queue()
        for i in range(len(self.nodes)):
            if todo[i] == 0:
                q.put(self.nodes[i])
        while not q.empty():
            node = q.get()
            vtree_node = self.get_vtree_node(node)
            for anc in node.ancestors:
                todo[anc.name] -= 1
                if todo[anc.name] == 0:
                    q.put(anc)
            if self.lca[separator_node][vtree_node] != separator_node:
                if node.type == Node.AND:
                    node.weight = np.empty(first_shape, dtype=first_semiring.dtype)
                    node.weight[:] = first_semiring.one()
                    for child in node.children:
                        child_vtree_node = self.get_vtree_node(child)
                        if self.lca[child_vtree_node][separator_node] == separator_node and child_vtree_node not in P:
                            node.weight *= np.array([ transform(w) for w in child.weight ])
                        else:
                            node.weight *= child.weight
                elif node.type == Node.OR:
                    node.weight = np.empty(first_shape, dtype=first_semiring.dtype)
                    node.weight[:] = first_semiring.zero()
                    for child in node.children:
                        node.weight += child.weight*factor(vtree_node, child.vtree_node)
            else:                
                if node.type == Node.AND:
                    node.weight = np.empty(second_shape, dtype=second_semiring.dtype)
                    node.weight[:] = second_semiring.one()
                    for child in node.children:
                        node.weight *= child.weight
                elif node.type == Node.OR:
                    node.weight = np.empty(second_shape, dtype=second_semiring.dtype)
                    node.weight[:] = second_semiring.zero()
                    for child in node.children:
                        node.weight += child.weight*factor(vtree_node, child.vtree_node)
        node.weight *= factor(node.vtree_node, self.vtree.idx)
        return node.weight

    def parse_wmc(self, path, weights, cnf): # path, weights, P, first_semiring, second_semiring, transform):
        """Performs (two) algebraic model counting over an X/D-constrained SDD while parsing it.
        
        Args:
            path (:obj:`string`): The path to the file that contains the SDD.
            weights (:obj:`string`): The weights of the literals. The weight for literal `v` is in `weights[2*(v-1)]`, the one for `-v` is in `weights[2*(v-1)+1]`
            P (:obj:`iterable`): The set of variables that are quantified over the first semiring.
            first_semiring (:obj:`module`): The module of the first semiring.
            second_semiring (:obj:`module`): The module of the second semiring.
            transform (:obj:`string`): The transformation function used to transform a value from the second semiring into a value from the first semiring.
                Will be used as

                        f_transform = eval(transform)
                        transform = lambda x : first_semiring.from_value(f_transform(x))
        Returns:
            (:obj:`object`): The algebraic model count.
        """
        shapes = [ (np.shape(weights[0])[0], ) + np.shape(semiring.one()) for semiring in cnf.semirings ]

        first_semiring = cnf.semirings[0]
        second_semiring = cnf.semirings[1]
        
        transform = cnf.transforms[0]

        P = cnf.quantified[0]        
        # initialize the transform function
        f_transform = eval(transform)
        transform = lambda x : first_semiring.from_value(f_transform(x))

        separator_node = self.separator_node(P)
        for i in range(len(weights)):
            if abs(to_dimacs(i)) not in P and self.lca[separator_node][abs(to_dimacs(i))] != separator_node: 
                weights[i] = np.array([ transform(w) for w in weights[i] ])
        
        index_to_node = { node.idx : node for node in self.vtree }
        index_to_node = [ index_to_node[i] for i in range(1, self.vtree.leaf_count()*2) ]

        def factor(i, j):
            if self.lca[i][j] == j: # i should always be above j
                i,j = j,i
            if self.lca[i][separator_node] == separator_node and i not in P:
                res = np.full(shapes[1], second_semiring.one())
            else:
                res = np.full(shapes[0], first_semiring.one())
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

        with open(path) as ddnnf:
            _, nr_nodes, nr_edges, nr_leafs = ddnnf.readline().split()
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
                        vtree_node = self.lca[vtree_nodes[int(line[2])]][vtree_nodes[int(line[3])]]
                        if self.lca[separator_node][vtree_node] != separator_node:
                            val = np.empty(shapes[0], dtype=first_semiring.dtype)
                            val[:] = first_semiring.one()
                            for x in line[2:]:
                                x = int(x)
                                child_vtree_node = vtree_nodes[x]
                                if self.lca[child_vtree_node][separator_node] == separator_node and child_vtree_node not in P:
                                    val *= np.array([ transform(w) for w in mem[x] ])
                                else:
                                    val *= mem[x]
                        else:
                            val = np.empty(shapes[1], dtype=second_semiring.dtype)
                            val[:] = second_semiring.one()
                            for x in line[2:]:
                                val *= mem[int(x)]
                    elif line[0] == 'O':
                        vtree_node = self.lca[vtree_nodes[int(line[3])]][vtree_nodes[int(line[4])]]
                        if self.lca[separator_node][vtree_node] != separator_node:
                            val = np.empty(shapes[0], dtype=first_semiring.dtype)
                            val[:] = first_semiring.zero()
                            for x in line[3:]:
                                val += mem[int(x)]*factor(vtree_node, vtree_nodes[int(x)])
                        else:                
                            val = np.empty(shapes[1], dtype=second_semiring.dtype)
                            val[:] = second_semiring.zero()
                            for x in line[3:]:
                                val += mem[int(x)]*factor(vtree_node, vtree_nodes[int(x)])
                mem.append(val)
                vtree_nodes.append(vtree_node)
                idx += 1
            mem[idx - 1] *= factor(vtree_node, self.vtree.idx)
            return mem[idx - 1]

