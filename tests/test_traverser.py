import networkx as nx
from unittest import TestCase

from rest.hierarchy_traverser import RelationshipInfo, unique_backward_paths, subgraphs, all_subgraphs


class HierarchyTraverserTest(TestCase):

    def setUp(self):
        self.g = nx.DiGraph()
        self.g.add_edge('root', 'level1_0')
        self.g.add_edge('root', 'level1_1')
        self.g.add_edge('level1_0', 'level2_0')
        self.g.add_edge('level1_0', 'level2_1')
        self.g.add_edge('level2_0', 'level3_0')

    def test_unique_backward_paths(self):
        correct_paths = [
            ['level3_0', 'level2_0', 'level1_0', 'root'],
            ['level2_0', 'level1_0', 'root'],
            ['level2_1', 'level1_0', 'root'],
            ['level1_0', 'root'],
            ['level1_1', 'root'],
            ['root'],
        ]
        paths = unique_backward_paths(self.g)
        self.assertEquals(len(correct_paths), len(paths))
        self.assertTrue(all(p in paths for p in correct_paths))

    def test_subgraphs(self):
        correct_subgraphs = [
            ['level3_0', 'level2_1', 'level1_1', 'level2_0', 'level1_0', 'root'],
            ['level1_0', 'level2_0', 'root'],
            ['level1_0', 'root'],
            ['root'],
        ]
        layers = [s.nodes() for s in all_subgraphs(self.g)]
        self.assertEquals(len(correct_subgraphs), len(layers))
        self.assertSequenceEqual(map(len, correct_subgraphs), map(len, layers))
        self.assertTrue(all([(set(cs) == set(layer)) for cs, layer in zip(correct_subgraphs, layers)]))

