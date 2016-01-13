from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.orm import RelationshipProperty

RELATION_BLACKLIST = ('query', 'query_class', '_sa_class_manager',
                      '_decl_class_registry')


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


def get_related_association_proxy_model(attr):
    prop = attr.remote_attr.property
    for attribute in ('mapper', 'parent'):
        if hasattr(prop, attribute):
            return getattr(prop, attribute).class_
    return None


def pk_attr_name(model):
    attrs_names = (attr_name for attr_name in dir(model)
                   if (not attr_name.startswith('__') and
                       not attr_name in RELATION_BLACKLIST))
    return find(is_pk(model), attrs_names)


def is_pk(model, attr_name):
    try:
        return getattr(model, attr_name).primary_key
    except AttributeError:
        return False


def find(predicate, iterable):
    return next((x for x in iterable if predicate(x)), None)
