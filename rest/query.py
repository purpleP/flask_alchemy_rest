from collections import namedtuple


QueryParam = namedtuple('QueryParam', 'model attr_name foreign_key_name foreign_key_value')


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
