from itertools import chain, repeat


def query(session, model_to_query, query_modifiers, keys):
    def f(query, query_modifier_values):
        query_modifier, values = query_modifier_values
        func_values = (query,) + values
        return query_modifier(*func_values)

    return reduce(f, zip_(query_modifiers, keys), session.query(model_to_query))


def filter_(left, query, right):
    return query.filter(left == right)


def join(left, right, query):
    return query.join(left, right)


def zip_(fss, values):
    vs = tuple(map(lambda v: (v,), values))
    if len(values) < len(fss):
        vs = ((),) + vs
        fss = (fss[0][1:], ) + fss[1:]

    return chain.from_iterable(
            [zip(fs, (v,) + tuple(repeat((), len(fs) - 1)))
             for fs, v in zip(fss, vs)])
