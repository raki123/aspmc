import queue
import sys
import numpy as np
import copy

class Node(object):
    AND = 0
    OR = 1
    NEG = 2
    IN = 3
    def __init__(self, type, name, children = None, ancestors = None):
        self.type = type
        self.name = name
        if children == None:
            self.children = []
        else:
            self.children = children
        if ancestors == None:
            self.ancestors = []
        else:
            self.ancestors = ancestors

class Circuit(object):
    def __init__(self, path):
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
                        to_add *= self.literals[(i-1)*2].weight + self.literals[(i-1)*2 + 1].weight
                    value += to_add
                node.weight = value
        for i in set(range(1, 1 + len(self.literals)//2)).difference(set(node.vars)):
            node.weight *= self.literals[(i-1)*2].weight + self.literals[(i-1)*2 + 1].weight
        return node.weight

    def wmc(self, weights):
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
    def parse_wmc(path, weights, zero = 0.0, one = 1.0, dtype = float):
        with open(path) as ddnnf:
            _, nr_nodes, nr_edges, nr_leafs = ddnnf.readline().split()
            mem = []
            idx = 0
            for line in ddnnf:
                line = line.strip().split()
                if line[0] == 'L':
                    val = weights[2*(abs(int(line[1]))-1) + (1 if int(line[1]) < 0 else 0)]
                elif line[0] == 'A':
                    val = np.full(len(weights[0]), one, dtype=dtype)
                    for x in line[2:]:
                        val *= mem[int(x)]
                elif line[0] == 'O':
                    val = np.full(len(weights[0]), zero, dtype=dtype)
                    for x in line[3:]:
                        val += mem[int(x)]
                mem.append(val)
                idx += 1
            return mem[idx - 1]

class MaxPlusFloat(object):
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        return self if self.value >= other.value else other

    def __iadd__(self, other):
        self.value = max(self.value, other.value)

    def __mul__(self, other):
        return MaxPlusFloat(self.value + other.value)

    def __imul__(self, other):
        self.value += other.value

    def __str__(self):
        return str(self.value)


class SRSet(object):
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        return SRSet(self.value | other.value)

    def __iadd__(self, other):
        self.value |= other.value

    def __mul__(self, other):
        return SRSet(self.value & other.value)

    def __imul__(self, other):
        self.value &= other.value

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)

if __name__ == "__main__":
    cnt = Circuit.parse_wmc(sys.argv[1], [np.array([MaxPlusFloat(1.0)])  for i in range(40000)], zero = MaxPlusFloat(-1.0), one = MaxPlusFloat(0.0))
    print(cnt[0])
    cnt = Circuit.parse_wmc(sys.argv[1], [np.array([SRSet(set([i]))])  for i in range(40000)], zero = SRSet(set()), one = SRSet(set(range(40000))))
    #circuit = Circuit(sys.argv[1])
    #cnt = circuit.non_smooth_wmc([np.array([1.0])  for i in range(40000)])
    print(cnt[0])
