from collections import namedtuple
from itertools import chain, groupby

from networkx import DiGraph, simple_cycles
from rest.helpers import inits
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


def break_cycles(graph):
    cycles = list(simple_cycles(graph))
    if len(cycles) == 0:
        return graph
    else:
        nodes = cycles[0]
        g1 = graph.copy()
        g1.remove_edge(nodes[-1], nodes[0])
    return break_cycles(g1)


def leaves(graph):
    return [n for n in graph.nodes_iter()
            if graph.out_degree(n) == 0 and
            graph.in_degree(n) in (0, 1)]


def all_paths(graph, node):
    cf = break_cycles(graph)
    subs = list(chain.from_iterable(map(inits, full_paths(cf, node))))
    return remove_duplicates(filter(lambda x: len(x) != 0, subs))


def full_paths(graph, node):
    if graph.out_degree(node) == 0:
        return iter([[node]])
    else:
        pss = [full_paths(graph, s)
               for s in graph.successors_iter(node) if s != node]
        return [list(chain([node], path)) for ps in pss for path in ps]


def remove_duplicates(list_of_lists):
    return [k for k, _ in groupby(sorted(list_of_lists))]
