from flask import jsonify
from rest.query import foreign_key_query, collection_query, item_query


def get_collection(db_session, query_params, schema, **kwargs):
    _, params = full_query_params(query_params, **kwargs)
    items = collection_query(db_session, params).all()
    return jsonify({'items': serialize_collection(schema, items)})


def get_collection_item(db_session, query_params, schema, primary_key_attr_name, **kwargs):
    ordered_ids = params = full_query_params(query_params, **kwargs)
    item = item_query(db_session, params, primary_key_attr_name, kwargs[ordered_ids[-1]]).one()
    return jsonify(serialize_item(schema, item))


def post_to_subcollection(db_session, query_params, schema, item):
    fk = foreign_key_query(db_session, query_params[1:])
    fk_name = query_params[0].foreign_key_name
    setattr(item, fk_name, fk)
    db_session.add(item)
    db_session.commit()
    return jsonify(serialize_item(schema, item))


def serialize_item(schema, item):
    return schema.dump(item).data


def serialize_collection(schema, collection):
    return schema.dump(collection, many=True).data


def full_query_params(query_params, **kwargs):
    ordered_ids = sorted(kwargs.keys())
    full_qp_reversed = [p._replace(foreign_key_value=kwargs[_id])
                        for p, _id in zip(reversed(query_params), ordered_ids)]
    return ordered_ids, tuple(reversed(full_qp_reversed))
