import json

from flask import jsonify, request
from marshmallow_sqlalchemy import ModelSchema
from rest.query import query
from sqlalchemy.orm.exc import NoResultFound


def get_collection(db_session, path, serializer, **kwargs):
    key_values = [kwargs[key] for key in sorted(kwargs.keys(), reverse=True)]
    cq = query(db_session, path, key_values)
    items = cq.all()
    return jsonify({'items': serializer(items)})


def get_item(db_session, path, serializer, **kwargs):
    args = [kwargs[key] for key in sorted(kwargs.keys(), reverse=True)]
    item_query = query(db_session, path, args)
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


def post_item(db_session, path, rel_attr_name,
              deserializer, item_as_dict, **kwargs):
    args = [kwargs[key] for key in sorted(kwargs.keys(), reverse=True)]
    _, exposed_attr = path[0]
    try:
        item = deserializer(item_as_dict)
        if len(path) == 1:
            db_session.add(item)
        else:
            parent = query(db_session, path[1:], args).one()
            db_session.add(parent)
            getattr(parent, rel_attr_name).append(item)
        db_session.commit()
        return jsonify({'id': getattr(item, exposed_attr)})
    except SchemaError as e:
        return json.dumps(e.errors), 400


def post_item_many_to_many(db_session, path, rel_attr_name, dict_, **kwargs):
    args = [kwargs[key] for key in sorted(kwargs.keys(), reverse=True)]
    _id = dict_['id']
    model, exposed_attr = path[0]
    item = db_session.query(model).filter(getattr(model, exposed_attr) == _id).one()
    parent = query(db_session, path[1:], args).one()
    db_session.add(parent)
    getattr(parent, rel_attr_name).append(item)
    db_session.commit()
    return '', 200


def delete_item(db_session, path, **kwargs):
    args = [kwargs[key] for key in sorted(kwargs.keys(), reverse=True)]
    query(db_session, path, args).delete(synchronize_session=False)
    return '', 200


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
