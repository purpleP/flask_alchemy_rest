from itertools import izip
from functools import partial


def query(session, model_to_query, attrs_to_filter, keys, join_attrs=()):

    def f(query, query_modifier):
        return query_modifier(query)

    initial_query = session.query(model_to_query)

    if len(join_attrs) > 0:
        initial_query = initial_query.join(*join_attrs)

    query_modifiers = [partial(filter_, a, k)
                       for a, k in izip(attrs_to_filter, keys)]

    return reduce(f, query_modifiers, initial_query)


def filter_(left, right, query):
    return query.filter(left == right)
