import numpy as np
from aspmc.util import *

class ConstrainedDDNNF(object):
    # assumes that the DDNNF is smooth
    @staticmethod
    def parse_wmc(path, weights, cnf):
        """Performs nested algebraic model counting over an X/D-constrained circuit that is smooth while parsing it.
        
        Args:
            path (:obj:`string`): The path to the file that contains the circuit.
            weights (:obj:`string`): The weights of the literals. The weight for literal `v` is in `weights[2*(v-1)]`, the one for `-v` is in `weights[2*(v-1)+1]`
            cnf (:obj:`aspmc.compile.CNF`): The CNF which was compiled. Must contain the semirings, quantification partition (telling us which variables are to be interpreted over which semiring), and the transformation functions:
                transform (:obj:`string`): The transformation function used to transform a value from the second semiring into a value from the first semiring.
                    Will be used as

                            f_transform = eval(transform)
                            transform = lambda x : first_semiring.from_value(f_transform(x))
        Returns:
            (:obj:`object`): The algebraic model count.
        """
        shapes = [ (np.shape(weights[0])[0], ) + np.shape(semiring.one()) for semiring in cnf.semirings ]
        
        # transforms[i][j] for i < j transforms a value from the jth semiring into one from the jth semiring
        transforms = [ [ None for _ in range(len(cnf.semirings)) ] for _ in range(len(cnf.semirings)) ]
        # set the base transforms
        base_transforms = [ eval(transform) for transform in cnf.transforms ]
        base_transforms = [ lambda x, transform = transform, i = i: cnf.semirings[i].from_value(transform(x)) for i, transform in enumerate(base_transforms) ]

        for i in range(len(cnf.semirings) - 1):
            transforms[i][i+1] = base_transforms[i]


        # set the multistep transforms
        for i in range(len(cnf.semirings) - 1, -1, -1):
            for j in range(i - 2, -1, -1):
                transforms[j][i] = lambda x, i = i, j = j: base_transforms[j](transforms[j+1][i](x))
                
        var_to_val_type = [ len(cnf.semirings) - 1 for _ in range(cnf.nr_vars + 1) ]
        for val_type, vars in enumerate(cnf.quantified):
            for var in vars:
                var_to_val_type[var] = val_type

        with open(path) as ddnnf:
            _, nr_nodes, nr_edges, nr_leafs = ddnnf.readline().split()
            mem = []
            mem_types = []
            idx = 0
            for line in ddnnf:
                line = line.strip().split()
                if line[0] == 'L':
                    val = weights[to_pos(int(line[1]))]
                    val_type = var_to_val_type[abs(int(line[1]))]
                else:
                    if line[0] == 'A':
                        val = None
                        val_type = None
                        for child in line[2:]:
                            child = int(child)
                            if mem_types[child] != val_type:
                                if val_type is None:
                                    val_type = mem_types[child]
                                    val = np.empty(shapes[val_type], dtype=cnf.semirings[val_type].dtype)
                                    val[:] = cnf.semirings[val_type].one()
                                    val *= mem[child]
                                else:
                                    if mem_types[child] < val_type:
                                        val = np.array([ transforms[mem_types[child]][val_type](w) for w in val ], dtype = cnf.semirings[mem_types[child]].dtype)
                                        val_type = mem_types[child]
                                        val *= mem[child]
                                    else:
                                        val *= np.array([ transforms[val_type][mem_types[child]](w) for w in mem[child] ], dtype = cnf.semirings[val_type].dtype)
                            else:
                                val *= mem[child]
                    elif line[0] == 'O':
                        val = None
                        val_type = None
                        for child in line[3:]:
                            child = int(child)
                            if mem_types[child] != val_type:
                                if val_type is None:
                                    val_type = mem_types[child]
                                    val = np.empty(shapes[val_type], dtype=cnf.semirings[val_type].dtype)
                                    val[:] = cnf.semirings[val_type].zero()
                                    val += mem[child]
                                else:
                                    if mem_types[child] < val_type:
                                        val = np.array([ transforms[mem_types[child]][val_type](w) for w in val ], dtype = cnf.semirings[mem_types[child]].dtype)
                                        val_type = mem_types[child]
                                        val += mem[child]
                                    else:
                                        val += np.array([ transforms[val_type][mem_types[child]](w) for w in mem[child] ], dtype = cnf.semirings[val_type].dtype)
                            else:
                                val += mem[child]
                mem.append(val)
                mem_types.append(val_type)
                idx += 1
            return mem[idx - 1]

