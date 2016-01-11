from itertools import chain, groupby, islice
from collections import namedtuple

from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.orm import RelationshipProperty

RELATION_BLACKLIST = ('query', 'query_class', '_sa_class_manager',
                      '_decl_class_registry')

RelationshipInfo = namedtuple('RelationshipInfo', 'fk_linked_attr_name fk_attr_name')
ModelInfo = namedtuple('ModelInfo', 'model url_attr')


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


def create_hierarchy(root_model):
    return


def leaves(graph):
    return [n for n in graph.nodes_iter()
            if graph.out_degree(n) == 0 and
            graph.in_degree(n) in (0, 1)]


def all_paths(graph, node):
    subs = chain.from_iterable(map(sublists, full_paths(graph, node)))
    return remove_duplicates(subs)


def sublists(iterable):
    return (islice(iterable, i + 1) for i, _ in enumerate(iterable))


def full_paths(graph, node):
    if graph.out_degree(node) == 0:
        return iter([[node]])
    else:
        pss = (full_paths(graph, s) for s in graph.successors_iter(node))
        return (chain([node], path) for ps in pss for path in ps)


def remove_duplicates(list_of_lists):
    return [k for k, _ in groupby(sorted(list_of_lists))]
