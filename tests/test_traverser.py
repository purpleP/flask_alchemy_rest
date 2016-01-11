from pytest import fixture

import networkx as nx

from rest.hierarchy_traverser import full_paths, sublists


@fixture
def graph():
    g = nx.DiGraph()
    g.add_edge('0', '1.0')
    g.add_edge('1.0', '2.0')
    g.add_edge('1.0', '2.1')
    g.add_edge('2.0', '3.0')
    g.add_edge('2.1', '3.1')
    return g


def test_sublist():
    a = xrange(3)
    correct_sublists = [
        [0],
        [0, 1],
        [0, 1, 2],
    ]
    assert map(list, sublists(a)) == correct_sublists


def test_paths(graph):
    correct_paths = [
        ['0', '1.0', '2.1', '3.1'],
        ['0', '1.0', '2.0', '3.0'],
    ]
    ps = full_paths(graph, '0')
    assert correct_paths == list(map(list, ps))
