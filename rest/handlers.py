import json
from functools import partial

from flask import jsonify, request
from marshmallow_sqlalchemy import ModelSchema
from rest.query import create_queries
from sqlalchemy.orm.exc import NoResultFound


def get_collection(db_session, query_params, serializer, **kwargs):
    _, params = full_query_params(query_params, **kwargs)
    collection_query, _, _ = create_queries(db_session, params)
    items = collection_query.all()
    return jsonify({'items': serializer(items)})


def get_item(db_session, query_params, serializer, **kwargs):
    ordered_ids, params = full_query_params(query_params, **kwargs)
    # TODO probably it would be more reasonable to query all and then check if there is only one
    _, item_query, _ = create_queries(db_session, params)
    try:
        item = item_query.one()
        return jsonify(serializer(item))
    except NoResultFound:
        return 'No such resource', 404


def post_item(db_session, query_params, deserializer, item_as_dict, **kwargs):
    _, params = full_query_params(query_params, **kwargs)
    _, _, fkq, = create_queries(db_session, query_params)
    try:
        item = deserializer(item_as_dict)
    except SchemaError as e:
        return json.dumps(e.errors), 400
    setattr(item, params[0].fk_attr, fkq.one())
    db_session.add(item)
    db_session.commit()
    return jsonify({'id': getattr(item, params[0].exposed_attr)})


class SchemaError(ValueError):
    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        return str(self.errors)


def deserialize_item(schema, db_session, item):
    result = schema.load(item, db_session)
    if len(result.errors) == 0:
        return result.data
    else:
        raise SchemaError(result.errors)


def serialize_item(schema, item):
    return schema.dump(item).data


def serialize_collection(schema, collection):
    return schema.dump(collection, many=True).data


def full_query_params(query_params, **kwargs):
    ordered_ids = sorted(kwargs.keys())
    full_qp_reversed = [p._replace(exposed_attr_value=kwargs[_id])
                        for p, _id in zip(reversed(query_params), ordered_ids)]
    return ordered_ids, tuple(reversed(full_qp_reversed))


def schema_class_for_model(model_class):
    schema_meta = type('Meta', (object,), {'model': model_class})
    return type(
            model_class.__name__ + 'Schema',
            (ModelSchema,),
            {'Meta': schema_meta}
    )


def flask_post_wrapper(actual_poster, **kwargs):
    return actual_poster(request.json, **kwargs)

