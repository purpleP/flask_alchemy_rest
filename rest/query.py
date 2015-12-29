from collections import namedtuple

QueryParam = namedtuple('QueryParam', 'model attr_name foreign_key_name foreign_key_value')
Relationship = namedtuple('Relationship', 'previous_level current_level next_level')


def create_query(db_session, query_params):
    model_to_query = query_params[0].model
    if query_params[0].attr_name:
        query = db_session.query(getattr(model_to_query, query_params[0].attr_name))
    else:
        query = db_session.query(model_to_query)
    if len(query_params) == 1:
        filter_value = query_params[0].foreign_key_value
    else:
        filter_value = create_query(db_session, query_params[1:])
    return query.filter(getattr(model_to_query, query_params[0].foreign_key_name) == filter_value)


def params_from_path(graph, path):
    relationships = [Relationship(p, c, n) for (p, c, n) in zip([None] + path, path, path[1:])]

    return tuple(QueryParam(
                model=r.current_level,
                attr_name=get_attr_name(graph, r.current_level, r.previous_level),
                foreign_key_name=graph[r.next_level][r.current_level]['rel'].fk_attr_name,
                foreign_key_value=None
            )
            for r in relationships)


def get_attr_name(graph, current, previous):
    try:
        return graph[current][previous]['rel'].fk_linked_attr_name
    except Exception:
        return None
