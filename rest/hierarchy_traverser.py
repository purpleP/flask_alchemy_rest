from collections import namedtuple
from itertools import chain
from split import groupby
from networkx import DiGraph, all_simple_paths
from rest.introspect import related_models
from six import iteritems
from six.moves import map, filter

ModelInfo = namedtuple('ModelInfo', 'model url_attr')


def create_graph(root_model):
    graph = DiGraph()
    add_model(graph, root_model)
    return graph


def add_model(graph, model):
    for m, rel_info in iteritems(related_models(model)):
        graph.add_edge(
            model,
            m,
            rel_attr=rel_info.attr,
            rel_type=rel_info.direction
        )
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
        return map(tuple, all_simple_paths(g, n1, n2))


def remove_duplicates(seq):
    seen = set()
    return filter(lambda x: not (x in seen or seen.add(x)), seq)
