import json

from functools import partial

from flask import jsonify, request
from marshmallow_sqlalchemy import ModelSchema
from rest.query import query
from sqlalchemy.orm.exc import NoResultFound


def get_collection(db_session, path, serializer, *keys, **kwargs):
    spec = kwargs.get('spec', lambda x: x)
    cq = query(db_session, path, keys)
    items = spec(cq).all()
    return jsonify(serializer(items))


def get_item(db_session, path, serializer, *keys):
    item_query = query(db_session, path, keys)
    try:
        item = item_query.one()
        return jsonify(serializer(item))
    except NoResultFound:
        return 'No such resource', 404


def post_item(db_session, path, rel_attr_name, deserializer, *keys, **kwargs):
    _, exposed_attr = path[0]
    data = kwargs.pop('data')
    try:
        item = deserializer(data)
        if len(path) == 1:
            db_session.add(item)
        else:
            parent = query(db_session, path[1:], keys).one()
            db_session.add(parent)
            getattr(parent, rel_attr_name).append(item)
        db_session.commit()
        return jsonify({'id': getattr(item, exposed_attr)})
    except SchemaError as e:
        return json.dumps(e.errors), 400
    except NoResultFound as e:
        return 'Parent resource not found', 404


def post_item_many_to_many(db_session, path, rel_attr_name, *keys, **kwargs):
    _id = kwargs.pop('data')['id']
    model, exposed_attr = path[0]
    item = db_session.query(model).filter(
            getattr(model, exposed_attr) == _id).one()
    try:
        parent = query(db_session, path[1:], keys).one()
        db_session.add(parent)
        getattr(parent, rel_attr_name).append(item)
        db_session.commit()
        return '', 200
    except NoResultFound as e:
        return 'Parent resource not found', 404



def patch_item(db_session, path, data, *keys, **kwargs):
    item_query = query(db_session, path, keys)
    try:
        item = item_query.one()
        db_session.add(item)
        for attr, new_value in data.iteritems():
            setattr(item, attr, new_value)
        db_session.commit()
    except NoResultFound:
        return 'No such resource', 404



def keys_from_kwargs(**kwargs):
    return tuple((kwargs[key] for key in sorted(kwargs.keys(), reverse=True)))


def create_handler(handler):
    def f(**kwargs):
        keys = keys_from_kwargs(**kwargs)
        return handler(*keys)
    return f


def get_handler(handler, specs={}):
    def f(**kwargs):
        spec_as_str = request.args.get('spec', None)
        h = handler
        if spec_as_str:
            spec_dict = json.loads(spec_as_str)
            try:
                spec = partial(specs[spec_dict['name']], *spec_dict['args'])
                h = partial(handler, spec=spec)
            except KeyError:
                return 'No such spec for this resource', 400
        return create_handler(h)(**kwargs)
    return f


def post_handler(handler):
    def f(**kwargs):
        return create_handler(partial(handler, data=request.json))(**kwargs)
    return f



def delete_item(db_session, path, *keys):
    db_session.delete(query(db_session, path, keys).one())
    db_session.commit()
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
    return {'items': schema.dump(collection, many=True).data}


def schema_maker(model_class, meta_dict={}):
    meta_dict['model'] = model_class
    schema_meta = type('Meta', (object,), meta_dict)
    return type(
            model_class.__name__ + 'Schema',
            (ModelSchema,),
            {'Meta': schema_meta}
    )


# def handle(db_session, path, serializer, query_creator,
#            fetch, spec=identity, *keys):
#     q = query(db_session, path, keys)
#     q = spec(q)
#     try:
#         data = fetch(q)
#         return jsonify(serializer(data))
#     except NoResultFound:
#         return 'No such resource', 404
#
#
# def get_collection_handler(handler):
#     return partial(handler, fetch=fetch_all)
#
#
# def get_item_handler(handler):
#     return partial(handler, fetch=fetch_one)


# def fetch_all(query):
#     return query.all()
#
#
# def fetch_one(query):
#     return query.one()
