from rest.helpers import find
from sqlalchemy import inspect
from collections import namedtuple


RelInfo = namedtuple('RelInfo', ['attr', 'direction'])


def related_models(model):
    m = inspect(model)
    return {r.mapper.class_: RelInfo(attr, r.direction)
            for attr, r in m.relationships.items()}


def pk_attr_name(model):
    attrs = [
        (attr, col_prop)
        for attr, col_prop in inspect(model).column_attrs.items()
    ]
    attr, column_prop = find(is_pk, attrs)
    return attr, column_prop.columns[0].type.python_type


def is_pk(attr_column):
    attr, col_prop = attr_column
    return find(lambda c: c.primary_key, col_prop.columns) is not None
