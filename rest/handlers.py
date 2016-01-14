import json
from functools import partial

from flask import jsonify, request
from marshmallow_sqlalchemy import ModelSchema
from rest.query import create_queries
from sqlalchemy.orm.exc import NoResultFound


def get_collection(db_session, fixed_query_params, serializer, **kwargs):
    args = [None] + [kwargs[key] for key in sorted(kwargs.keys(), reverse=True)]
    cq, _, _ = create_queries(db_session, fixed_query_params, args)
    items = cq.all()
    return jsonify({'items': serializer(items)})


def get_item(db_session, fixed_query_params, serializer, **kwargs):
    args = [kwargs[key] for key in sorted(kwargs.keys(), reverse=True)]
    _, item_query, _ = create_queries(db_session, fixed_query_params, args)
    try:
        item = item_query.one()
        return jsonify(serializer(item))
    except NoResultFound:
        return 'No such resource', 404


# TODO Think about how to remove code duplication in functional style
# def handle(db_session, query_params, do_stuff, **kwargs):
#     args = [kwargs[key] for key in sorted(kwargs.keys())]
#     cq, iq, fkq = create_queries(db_session, query_params, **kwargs)
#     return do_stuff(cq, iq, fkq)


def post_item(db_session, fixed_query_params,
              deserializer, item_as_dict, **kwargs):
    args = [kwargs[key] for key in sorted(kwargs.keys(), reverse=True)]
    _, _, fkq, = create_queries(db_session, fixed_query_params[1:], args)
    _, exposed_attr, fk_attr, linked_attr = fixed_query_params[0]
    try:
        item = deserializer(item_as_dict)
    except SchemaError as e:
        return json.dumps(e.errors), 400
    setattr(item, fixed_query_params[0].fk_attr,
            fkq(linked_attr=linked_attr).one()[0])
    db_session.add(item)
    db_session.commit()
    return jsonify({'id': getattr(item, exposed_attr)})


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


def schema_class_for_model(model_class):
    schema_meta = type('Meta', (object,), {'model': model_class})
    return type(
            model_class.__name__ + 'Schema',
            (ModelSchema,),
            {'Meta': schema_meta}
    )


def flask_post_wrapper(actual_poster, **kwargs):
    return actual_poster(request.json, **kwargs)
