import itertools
from collections import namedtuple

import operator

from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.orm import RelationshipProperty

RELATION_BLACKLIST = ('query', 'query_class', '_sa_class_manager',
                      '_decl_class_registry')

RelationshipInfo = namedtuple('RelationshipInfo', 'rel_name fk_name')


def create_hierarchy(root_model):
    return


def unique_backward_paths(graph):
    return remove_duplicates(
            reduce(operator.concat, [backward_hierarchies(g) for g in all_subgraphs(graph)], [])
    )


def get_rels(model):
    attrs_relations = ((attr_name, get_relation_class_for(model, attr_name)) for attr_name in dir(model))
    return [(attr_name, relation_class) for attr_name, relation_class in attrs_relations if relation_class]


def get_relation_class_for(model, attr_name):
    if attr_name.startswith('__') or attr_name in RELATION_BLACKLIST:
        return None
    else:
        attr = getattr(model, attr_name)
        if hasattr(attr, 'property') \
                and isinstance(attr.property, RelationshipProperty):
            return attr.property.mapper.class_
        if isinstance(attr, AssociationProxy):
            return get_related_association_proxy_model(attr)


# TODO make this method more clear
def get_related_association_proxy_model(attr):
    prop = attr.remote_attr.property
    for attribute in ('mapper', 'parent'):
        if hasattr(prop, attribute):
            return getattr(prop, attribute).class_
    return None


def leaves(graph):
    return [n for n in graph.nodes_iter()
            if graph.out_degree(n) == 0 and
            graph.in_degree(n) in (0, 1)]


def parents_in_order(g, leaf):
    predecessors = g.predecessors(leaf)
    if len(predecessors) == 0:
        return []
    else:
        return [predecessors[0]] + parents_in_order(g, predecessors[0])


def without_leaves(graph):
    g = graph.copy()
    g.remove_nodes_from(leaves(graph))
    return g


def all_subgraphs(graph):
    return [graph] + subgraphs(graph)


def subgraphs(graph):
    if graph.size() == 0:
        return []
    else:
        subgraph = without_leaves(graph)
        return [subgraph] + subgraphs(subgraph)


def backward_hierarchies(graph):
    return [[leaf] + parents_in_order(graph, leaf) for leaf in leaves(graph)]


def remove_duplicates(list_of_lists):
    return [k for k, _ in itertools.groupby(sorted(list_of_lists))]
