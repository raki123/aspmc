import networkx as nx
import logging

import aspmc.graph.treedecomposition as treedecomposition

import aspmc.compile.vtree as vtree
import aspmc.compile.dtree as dtree

import aspmc.config as config

logger = logging.getLogger("aspmc")

def compute_separator(graph, P, D, R):
    if len(P) == 0 or len(R) == 0:
        return []
    flow_graph = nx.DiGraph()
    N = graph.number_of_nodes()
    # 1 to N are nodes for incoming edges
    # N + 1 to 2*N are nodes for outgoing edges
    # the edges between i, i + N for i in P or D are the 
    # only ones that can be cut
    for i in P:
        flow_graph.add_edge(i, i + N, capacity = 1.0)
    for i in D:
        flow_graph.add_edge(i, i + N, capacity = 1.0)
    for i in R:
        # these are edges with infinite capacity
        flow_graph.add_edge(i, i + N)
        
    for u,v in graph.edges:
        flow_graph.add_edge(u + N, v)
        flow_graph.add_edge(v + N, u)
    
    # add global source and sink
    source = 2*N + 1
    sink = 2*N + 2
    flow_graph.add_node(source)
    flow_graph.add_node(sink)
    for i in R:
        flow_graph.add_edge(source, i)
    for i in P:
        flow_graph.add_edge(i + N, sink)
        
    cut_value, partition = nx.minimum_cut(flow_graph, source, sink)
    reachable, non_reachable = partition
    cutset = set()
    for u, nbrs in ((n, flow_graph[n]) for n in reachable):
        cutset.update((u, v) for v in nbrs if v in non_reachable)
    return [ u for u, _ in cutset ]

def TD_to_tree(cnf, td, done = None, tree_type = dtree.Dtree):
    if tree_type.__name__ is dtree.Dtree.__name__:
        return dtree.TD_to_dtree(cnf, td, done = done)
    elif tree_type.__name__ == vtree.Vtree.__name__:
        return vtree.TD_to_vtree(td)
    else:
        logger.error(f"Unknown tree type {tree_type}")
        exit(-1)

def from_order(cnf, order, done = None, tree_type = dtree.Dtree):
    if tree_type.__name__ is dtree.Dtree.__name__:
        return dtree.from_order(cnf, order, done = done)
    elif tree_type.__name__ == vtree.Vtree.__name__:
        return vtree.from_order(order)
    else:
        logger.error(f"Unknown tree type {tree_type}")
        exit(-1)


def tree_from_cnf(cnf, tree_type = dtree.Dtree):    
    """Constructs an X/D-constrained Vtree or Dtree for the given cnf.

    Does this by: 

    * getting the atoms `X` from `cnf.quanfied[0]`. So the atoms that are quantified over the first semiring.
    * getting the atoms `D` that are defined by `X` w.r.t. the cnf.
    * getting a separator `S` between the atoms in `X` and the ones neither in `X` nor `D` using atoms from `X` or `D`.
    * the constructed X/D-constrained D/Vtree then ensures that all the atoms in `S` are decided first,
        meaning that all the atoms in `X` can be decided before/independently of the atoms that are not in `X` or `D`.
    * if there are more than two semirings, this is repeated recursively.

    Args:
        cnf (:obj:`aspmc.compile.cnf.CNF`): The extended cnf for which a tree should be constructed. Must have exactly two semirings.
        tree_type (:obj:`type`, optional): The type of tree to construct. 
            Must be one of `aspmc.compile.dtree.Dtree` and `aspmc.compile.vtree.Vtree`.
            Defaults to `aspmc.compile.dtree.Dtree`.
    Returns:
        (iterable, aspmc.graph.bintree.bintree): 

        The vertices in the separator(s) `S` that was (were) computed.
        
        The root of the D/Vtree that was constructed.
    """
    P = set()
    D = set()
    R = set(range(1,cnf.nr_vars + 1))
    graph = cnf.primal_graph()
    separators = []
    for i in range(len(cnf.quantified) - 1):
        P.update(cnf.quantified[i])
        R.difference_update(cnf.quantified[i])
        
        if config.config["constrained"] == "XD":
            D = cnf.get_defined(P)
            R.difference_update(D)
        
        # split the whole graph into two graphs that only contain nodes from P U D or R U D 
        separator = compute_separator(graph, P, D, R)
        logger.debug(f"Size of the {i}-th separator: {len(separator)}")
        separators.append(separator)
        
        # remove all edges that use separator nodes from the graph
        graph.remove_nodes_from(separator)
        # readd the nodes for invariance reasons
        graph.add_nodes_from(separator)
    
    graph = cnf.primal_graph()
    tree = construct_tree(cnf, graph, separators, tree_type = tree_type)
    
    # gather all variables that occur in a separator 
    all_separators = set()
    for separator in separators:
        all_separators.update(separator)
    return [all_separators, tree]

def construct_tree(cnf, graph, separators, tree_type = dtree.Dtree):
    done = None
    if tree_type.__name__ is dtree.Dtree.__name__: 
        # remember which clauses have been taken care of already
        done = [ False for _ in range(len(cnf.clauses)) ]
        
    left_trees = []
    working_graph = graph.copy()
    overall_l_components = set()
    previous_separators = set()
    for level in range(len(cnf.quantified) - 1):
        separator = separators[level]
        previous_separators.update(separator)
        P = cnf.quantified[level]    
        # if the separator is empty we know all variables are defined or P is empty
        # either way, we have no restrictions here
        if len(separator) == 0:
            left_trees.append(None)
            continue
        
        # remove the nodes from the graph
        working_graph.remove_nodes_from(separator)

        # build the graphs that contain only nodes from P U D or R U D respectively
        l_components = set()
        for component in nx.connected_components(working_graph):
            if P & component:
                l_components.update(component)

        overall_l_components.update(l_components)

        if len(l_components) == 0:
            # we used P as the separator
            left_trees.append(None)
        else:
            # also remove the left part from the working graph
            working_graph.remove_nodes_from(l_components)
            # we found a better separator than P
            l_components.update(previous_separators)
            l_graph = graph.subgraph(l_components).copy()
            separator = list(separator)
            clique = sum([ [ (separator[a], separator[b]) for a in range(b + 1, len(separator)) ] for b in range(len(separator)) ], [])
            l_graph.add_edges_from(clique)
            l_td = treedecomposition.from_graph(l_graph, solver = config.config["decos"], timeout = config.config["decot"])
            logger.info(f"X/D-Constrained Tree Decomposition #bags: {l_td.bags} treewidth: {l_td.width} #vertices: {l_td.vertices}")
            l_root = l_td.find_containing(separator)
            l_td.set_root(l_root)
            if tree_type.__name__ == vtree.Vtree.__name__:
                l_td.remove(separator)
            l_tree = TD_to_tree(cnf, l_td, done = done, tree_type = tree_type)
            left_trees.append(l_tree)
            
    right_graph = graph.copy()
    right_graph.remove_nodes_from(overall_l_components)
    for level in range(len(cnf.quantified) - 1):
        separator = separators[level]
        separator = list(separator)
        clique = sum([ [ (separator[a], separator[b]) for a in range(b + 1, len(separator)) ] for b in range(len(separator)) ], [])
        right_graph.add_edges_from(clique)
    right_td = treedecomposition.from_graph(right_graph, solver = config.config["decos"], timeout = config.config["decot"])
    logger.info(f"X/D-Constrained Tree Decomposition #bags: {right_td.bags} treewidth: {right_td.width} #vertices: {right_td.vertices}")
    
    r_root = right_td.find_containing(separators[0])
    assert(r_root is not None)
    right_td.set_root(r_root)
    
    if tree_type.__name__ == vtree.Vtree.__name__:
        for level in range(len(cnf.quantified) - 1):
            separator = separators[level]
            right_td.remove(separator)
            
    parent = TD_to_tree(cnf, right_td, done = done, tree_type = tree_type)
    # all materials are in place
    # construct the complete tree by bottom up stitching
    for level in range(len(separators) - 1, -1, -1):
        separator = separators[level]
        
        if len(separator) == 0:
            # we do not have to do anything
            continue
        
        # first combine right and left
        if parent is None:
            parent = left_trees[level]
        elif left_trees[level] is None:
            pass
        else:
            new_parent = tree_type()
            new_parent.left = left_trees[level]
            new_parent.right = parent
            parent = new_parent
            
        sep_tree = from_order(cnf, separator, done = done, tree_type = tree_type)
        
        # find out where to put the parent
        last = None
        cur = sep_tree
        while not cur.right is None:
            last = cur
            cur = cur.right
        grandparent = tree_type()
        if not last is None:
            last.right = grandparent
        else:
            sep_tree = grandparent
        grandparent.left = cur
        grandparent.right = parent
        
        parent = sep_tree
        
    if tree_type.__name__ is dtree.Dtree.__name__ and not all(done):
        logger.error("Not all clauses are in the dtree.")
        exit(-1)
        
    return parent
            