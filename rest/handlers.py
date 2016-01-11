import json
from functools import partial

from flask import jsonify, request
from marshmallow_sqlalchemy import ModelSchema
from pymonad import curry
from rest.query import foreign_key_query, collection_query, item_query
from sqlalchemy.orm.exc import NoResultFound


@curry
def get_collection(db_session, query_params, serializer, **kwargs):
    _, params = full_query_params(query_params, **kwargs)
    items = collection_query(db_session, params).all()
    return jsonify({'items': serializer(items)})


@curry
def get_collection_item(db_session, query_params, serializer, primary_key_attr_name, **kwargs):
    ordered_ids, params = full_query_params(query_params, **kwargs)
    # TODO probably it would be more reasonable to query all and then check if there is only one
    try:
        item = item_query(db_session, params, primary_key_attr_name, kwargs[ordered_ids[-1]]).one()
        return jsonify(serializer(item))
    except NoResultFound:
        return 'No such resource', 404


@curry
def post_item(db_session, query_params, deserializer, key_to_use_in_url, item_as_dict, **kwargs):
    _, params = full_query_params(query_params, **kwargs)
    fk_name = params[0].foreign_key_name
    fk, = foreign_key_query(db_session, params[1:]).one()
    try:
        item = deserializer(item_as_dict)
    except SchemaError as e:
        return json.dumps(e.errors), 400
    setattr(item, fk_name, fk)
    db_session.add(item)
    db_session.commit()
    return jsonify({'id': getattr(item, key_to_use_in_url)})


class SchemaError(ValueError):
    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        return str(self.errors)


@curry
def deserialize_item(schema, db_session, item):
    result = schema.load(item, db_session)
    if len(result.errors) == 0:
        return result.data
    else:
        raise SchemaError(result.errors)


@curry
def serialize_item(schema, item):
    return schema.dump(item).data


@curry
def serialize_collection(schema, collection):
    return schema.dump(collection, many=True).data


def full_query_params(query_params, **kwargs):
    ordered_ids = sorted(kwargs.keys())
    full_qp_reversed = [p._replace(foreign_key_value=kwargs[_id])
                        for p, _id in zip(reversed(query_params), ordered_ids)]
    return ordered_ids, tuple(reversed(full_qp_reversed))


def schema_class_for_model(model_class):
    schema_meta = type('Meta', (object,), {'model': model_class})
    return type(
            model_class.__name__ + 'Schema',
            (ModelSchema,),
            {'Meta': schema_meta}
    )


def default_serializer_or_deserializer(func, model, db_session):
    return partial(func, schema_class_for_model(model), db_session)


def post_flask_wrapper(actual_poster, **kwargs):
    return actual_poster(request.json, **kwargs)


