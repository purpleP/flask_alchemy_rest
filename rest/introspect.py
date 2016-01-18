from functools import partial

from sqlalchemy import inspect
from sqlalchemy.ext.associationproxy import AssociationProxy

RELATION_BLACKLIST = ('query', 'query_class', '_sa_class_manager',
                      '_decl_class_registry')


def related_models(model):
    m = inspect(model)
    relationships = [r.mapper.class_ for r in m.relationships.values()]
    ds = [d for d in m.all_orm_descriptors.values()
          if isinstance(d, AssociationProxy)]

    return relationships + []


def relation_info(child_model, parent_model):
    ch_m = inspect(child_model)
    p_m = inspect(parent_model)
    result = [(attr, list(column.foreign_keys)[0])
              for attr, column in ch_m.columns.items()
              if list(column.foreign_keys)[0].table == p_m.table][0]
    fk_attr, linked_column = result
    linked_attr, _ = find(lambda i: i[1] == linked_column, p_m.columns.items())
    return fk_attr, linked_attr


# TODO use inspect instead
def pk_attr_name(model):
    attrs_names = (attr_name for attr_name in dir(model)
                   if (not attr_name.startswith('__') and
                       not attr_name in RELATION_BLACKLIST))
    return find(partial(is_pk, model), attrs_names)


def is_pk(model, attr_name):
    try:
        return getattr(model, attr_name).primary_key
    except AttributeError:
        return False


def find(predicate, iterable):
    return next((x for x in iterable if predicate(x)), None)
