from collections import namedtuple
from itertools import chain, groupby, islice

RelationshipInfo = namedtuple('RelationshipInfo', 'fk_linked_attr_name fk_attr_name')
ModelInfo = namedtuple('ModelInfo', 'model url_attr')




def create_hierarchy(root_model):
    return


def leaves(graph):
    return [n for n in graph.nodes_iter()
            if graph.out_degree(n) == 0 and
            graph.in_degree(n) in (0, 1)]


def all_paths(graph, node):
    subs = chain.from_iterable(map(sublists, full_paths(graph, node)))
    return remove_duplicates(list(subs))


def sublists(_list):
    return [_list[: i + 1] for i, _ in enumerate(_list)]


def full_paths(graph, node):
    if graph.out_degree(node) == 0:
        return iter([[node]])
    else:
        pss = [full_paths(graph, s) for s in graph.successors_iter(node)]
        return [list(chain([node], path)) for ps in pss for path in ps]


def remove_duplicates(list_of_lists):
    return [k for k, _ in groupby(sorted(list_of_lists))]
