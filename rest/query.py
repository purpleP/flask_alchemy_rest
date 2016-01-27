def query(session, model_to_query, query_modifiers, keys):
    def f(query, query_modifier_key):
        query_modifier, key = query_modifier_key
        return query_modifier(query=query, right=key)

    if len(keys) < len(query_modifiers):
        query_modifiers = query_modifiers[1:]

    return reduce(f, zip(query_modifiers, keys), session.query(model_to_query))


def filter_(query, left, right):
    return query.filter(left == right)


def join(query, left, right):
    return query.join(left, right)


def join_and_filter(query, left_join, right_join, left, right):
    return filter_(join(query, left_join, right_join), left, right)




