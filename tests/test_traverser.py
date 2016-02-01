from operator import eq

from networkx.algorithms.isomorphism.isomorph import is_isomorphic
from pytest import fixture

import networkx as nx

from rest.hierarchy_traverser import create_graph, all_paths
from rest.helpers import inits
from tests.fixtures import Root, Parent, models_graphs


@fixture
def graph():
    g = nx.DiGraph()
    g.add_edge('0', '1.0')
    g.add_edge('1.0', '2.0')
    g.add_edge('1.0', '2.1')
    g.add_edge('2.0', '3.0')
    g.add_edge('2.1', '3.1')
    return g


@fixture
def graph_with_cycles(graph):
    g = graph.copy()
    g.add_edge('2.1', '2.0')
    g.add_edge('2.0', '2.1')
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


def graph_isom(graph1, graph2):
    return is_isomorphic(graph1, graph2, node_match=eq, edge_match=eq)


def test_all_paths(graph):
    correct_paths = (
        ('0',),
        ('0', '1.0'),
        ('0', '1.0', '2.0'),
        ('0', '1.0', '2.0', '3.0'),
        ('0', '1.0', '2.1'),
        ('0', '1.0', '2.1', '3.1'),
    )
    paths = map(tuple, all_paths(graph, '0'))
    assert set(paths) == set(correct_paths)
    graph.add_edge('2.0', '2.1')
    graph.add_edge('2.1', '2.0')
    paths = map(tuple, all_paths(graph, '0'))
    correct_paths = (
        ('0',),
        ('0', '1.0'),
        ('0', '1.0', '2.0'),
        ('0', '1.0', '2.0', '3.0'),
        ('0', '1.0', '2.1'),
        ('0', '1.0', '2.1', '3.1'),
        ('0', '1.0', '2.1', '2.0'),
        ('0', '1.0', '2.0', '2.1'),
        ('0', '1.0', '2.0', '2.1', '3.1'),
        ('0', '1.0', '2.1', '2.0', '3.0'),
    )
    assert set(paths) == set(correct_paths)
