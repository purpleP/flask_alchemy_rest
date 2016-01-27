from functools import partial
from operator import eq

from networkx.algorithms.isomorphism.isomorph import is_isomorphic
from pytest import fixture

import networkx as nx

from rest.hierarchy_traverser import full_paths, tails, create_graph, \
    cycle_free_graphs, all_paths
from rest.helpers import inits, tails
from rest.introspect import find
from tests.fixtures import Root, models_graphs, Parent, Child


@fixture
def graph():
    g = nx.DiGraph()
    g.add_edge('0', '1.0')
    g.add_edge('1.0', '2.0')
    g.add_edge('1.0', '2.1')
    g.add_edge('2.0', '3.0')
    g.add_edge('2.1', '3.1')
    return g


def test_inits():
    a = range(3)
    correct_inits = [
        [],
        [0],
        [0, 1],
        [0, 1, 2],
    ]
    assert inits(a) == correct_inits


def test_create_hierarchy(models_graphs):
    hierarchy_graph, cyclic_graph = models_graphs
    g = create_graph(Root)
    assert is_isomorphic(g, hierarchy_graph, node_match=eq, edge_match=eq)
    g = create_graph(Parent)
    assert is_isomorphic(g, cyclic_graph, node_match=eq, edge_match=eq)


def test_cycle_free_graphs(models_graphs):
    hierarchy, cyclic_graph = models_graphs
    cf1 = cyclic_graph.copy()
    cf1.remove_edge(Child, Parent)
    cf2 = cyclic_graph.copy()
    cf2.remove_edge(Parent, Child)
    cf_graphs = cycle_free_graphs(cyclic_graph)
    correct_graphs = [cf1, cf2]

    for cf in cf_graphs:
        check = partial(is_isomorphic, cf, node_match=eq, edge_match=eq)
        isom = find(check, correct_graphs)
        assert isom is not None
        correct_graphs.remove(isom)

    cf_graphs = cycle_free_graphs(hierarchy)
    assert len(cf_graphs) == 1
    assert is_isomorphic(hierarchy, cf_graphs[0], node_match=eq, edge_match=eq)


def test_tails():
    a = range(3)
    corret_tails = [
        [0, 1, 2],
        [1, 2],
        [2],
        [],
    ]
    assert tails(a) == corret_tails


def test_all_paths(graph):
    correct_paths = [
        ['0'],
        ['0', '1.0'],
        ['0', '1.0', '2.0'],
        ['0', '1.0', '2.0', '3.0'],
        ['0', '1.0', '2.1'],
        ['0', '1.0', '2.1', '3.1'],
    ]
    paths = all_paths(graph, '0')
    assert paths == correct_paths
    graph.add_edge('0', '2.0')
    graph.add_edge('2.0', '1.0')
    paths = all_paths(graph, '0')
    correct_paths = [
        ['0'],
        ['0', '1.0'],
        ['0', '1.0', '2.0'],
        ['0', '1.0', '2.0', '3.0'],
        ['0', '1.0', '2.1'],
        ['0', '1.0', '2.1', '3.1'],
        ['0', '2.0'],
        ['0', '2.0', '1.0'],
        ['0', '2.0', '1.0', '2.1'],
        ['0', '2.0', '1.0', '2.1', '3.1'],
        ['0', '2.0', '3.0'],
    ]
    assert paths == correct_paths


def test_paths(graph):
    correct_paths = [
        ['0', '1.0', '2.1', '3.1'],
        ['0', '1.0', '2.0', '3.0'],
    ]
    ps = full_paths(graph, '0')
    assert correct_paths == ps
