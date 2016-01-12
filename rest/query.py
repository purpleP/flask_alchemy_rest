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


def filter_query(query, model, filter_attr, filter_value):
    return query.filter(getattr(model, filter_attr), filter_value)


def create_q(db_session, models, params):
    model = models[-1]
    exposed_attr, fk_attr, fk_to_attr = params[-1]
    f = partial(filter_query, model=model, filter_attr=exposed_attr)
    if len(models) == 1: 
        cq = db_session.query(model)
        iq = partial(f, query=cq)
        return cq, iq, f
    else:
        parent_model = models[-2]
        _cq, _iq, _f = create_query(db_session, models[1:], params[1:])
        cq = db_session.query(model).filter(
            getattr(model, fk_attr) == _f(db_session.query(getattr(parent_model, fk_to_attr)))
        )
        iq = partial(f, query=cq)



root_colq = db_session.query(Root)
root_item_query = root_colq.filter(Root.name == 'root')
level1_colq = db_session.query(Level1).filter(Level1.root_pk ==
                                db_session.query(Root.name).filter(Root.name == 'root')
                                )
level1_itemq = level1_colq.filter(Level.name == 'level1')
level2_colq = db_session.query(Level2).filter(
    Level2.level1_pk == db_session.query(Level1.name).filter(Level1.root_pk ==
                                db_session.query(Root.name).filter(Root.name == 'root')
                                )
)
