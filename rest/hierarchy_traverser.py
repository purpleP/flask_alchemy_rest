from collections import namedtuple
from itertools import chain, groupby

from networkx import DiGraph, all_simple_paths
from rest.introspect import related_models

ModelInfo = namedtuple('ModelInfo', 'model url_attr')


def create_graph(root_model):
    graph = DiGraph()
    add_model(graph, root_model)
    return graph


def add_model(graph, model):
    for m, rel_attr in related_models(model).iteritems():
        graph.add_edge(model, m, rel_attr=rel_attr)
        if (m, model) not in graph.edges():
            add_model(graph, m)


def leaves(graph):
    return [n for n in graph.nodes_iter()
            if graph.out_degree(n) == 0 and
            graph.in_degree(n) in (0, 1)]


def all_paths(graph, node):
    sps = chain.from_iterable(
        (_paths(graph, node, n) for n in graph.nodes_iter())
    )
    return remove_duplicates(sps)


def _paths(g, n1, n2):
    if n1 == n2:
        return (n1,),
    else:
        return all_simple_paths(g, n1, n2)


def remove_duplicates(list_of_lists):
    return (tuple(k) for k, _ in groupby(sorted(list_of_lists)))
