from collections import namedtuple

import itertools

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


def item_query(db_session, query_params, key_attr_name, key_value):
    model_to_query = query_params[0].model
    query = collection_query(db_session, query_params)
    return query.filter(getattr(model_to_query, key_attr_name) == key_value)


def top_level_collection_query(db_session, query_params):
    return db_session.query(query_params[0].model)


def collection_query(db_session, query_params):
    if len(query_params) == 1:
        return top_level_collection_query(db_session, query_params)
    else:
        return subcollection_query(db_session, query_params)


def subcollection_query(db_session, query_params):
    model_to_query = query_params[0].model
    query = db_session.query(model_to_query)
    fk = foreign_key_query(db_session, query_params[1:])
    fk_name = query_params[0].foreign_key_name
    return query.filter(getattr(model_to_query, fk_name) == fk)


def foreign_key_query(db_session, query_params):
    model_to_query = query_params[0].model
    query = db_session.query(getattr(model_to_query, query_params[0].attr_name))
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


def url_for_path(graph, path):
    resources_names = [model.__tablename__ for model in reversed(path)]
    url_parts = [''] + list(itertools.chain(
            *[[resources_name, '<level_{}_id>'.format(i)] for i, resources_name in enumerate(resources_names)]
    )
    )
    collection_resource_url = '/'.join(url_parts[:-1])
    item_resource_url = '/'.join(url_parts)
    return collection_resource_url, item_resource_url


# TODO make every node connected to itself with relationship with None attributes
# then there would be no need in try except
def get_attr_name(graph, current, previous):
    try:
        return graph[current][previous]['rel'].fk_linked_attr_name
    except Exception:
        return None
