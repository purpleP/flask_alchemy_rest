import sys
import string as s
from random import uniform, randint, choice
from itertools import chain
from rstr import rstr, xeger
from functools import reduce
from split import groupby


def number(schema):
    return uniform(schema['minimum'], schema['maximum'])


def integer(schema):
    return randint(
        schema.get('minimum', -sys.maxsize),
        schema.get('maximum', sys.maxsize)
    )


def string(schema):
    pattern = schema.get('pattern', None)
    if pattern:
        return xeger(pattern)
    return rstr(s.ascii_uppercase + s.digits)


def boolean(schema):
    return choice((True, False))


def array(schema):
    pass


def object_(schema):
    props = dict(groupby(
        lambda name_p: name_p[0] in schema['required'],
        schema['properties'].iteritems()
    ))
    included_non_required = ((name, p) for name, p in props.get(False, ())
                             if choice((True, False)))
    props_to_convert = chain(props[True], included_non_required)
    return reduce(random_property, props_to_convert, {})


def random_property(acc, name_schema):
    name, schema = name_schema
    acc[name] = mapping[schema['type']](schema)
    return acc


mapping = {
    'string': string,
    'integer': integer,
    'number': number,
    'boolean': boolean,
    'object': object_,
}
