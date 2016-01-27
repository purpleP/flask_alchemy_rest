import json

from functools import partial

from flask import jsonify, request
from marshmallow_sqlalchemy import ModelSchema
from rest.query import query
from sqlalchemy.orm.exc import NoResultFound


def get_collection(db_session, query, serializer, *keys, **kwargs):
    spec = kwargs.get('spec', lambda x: x)
    cq = query(session=db_session, keys=keys)
    items = spec(cq).all()
    return jsonify(serializer(items))


def get_item(db_session, query, serializer, *keys):
    item_query = query(session=db_session, keys=keys)
    try:
        item = item_query.one()
        return jsonify(serializer(item))
    except NoResultFound:
        return 'No such resource', 404


def post_item(db_session, exposed_attr, adder, deserializer, *keys, **kwargs):
    try:
        item = deserializer(kwargs.pop('data'))
        adder(db_session, item, *keys)
        db_session.commit()
        return jsonify({'id': getattr(item, exposed_attr)})
    except SchemaError as e:
        return json.dumps(e.errors), 400
    except NoResultFound as e:
        return 'Parent resource not found', 404


def root_adder(db_session, item, *keys):
    db_session.add(item)


def non_root_adder(query, rel_attr_name, db_session, item, *keys):
    parent = query(session=db_session, keys=keys).one()
    db_session.add(parent)
    getattr(parent, rel_attr_name).append(item)


def post_item_many_to_many(db_session, item_query, parent_query, rel_attr_name,
                           *keys, **kwargs):
    try:
        _id = kwargs.pop('data')['id']
        item = item_query(session=db_session, keys=(_id,)).one()
        parent = parent_query(session=db_session, keys=keys).one()
        db_session.add(parent)
        getattr(parent, rel_attr_name).append(item)
        db_session.commit()
        return '', 200
    except NoResultFound as e:
        return 'Parent resource not found', 404


def delete_item(db_session, query, *keys):
    db_session.delete(query(session=db_session, keys=keys).one())
    db_session.commit()
    return '', 200


def delete_many_to_many(db_session, item_query, parent_query, rel_attr_name, *keys):
    item = item_query(session=db_session, keys=keys).one()
    parent = parent_query(session=db_session, keys=keys[1:]).one()
    db_session.add(parent)
    getattr(parent, rel_attr_name).remove(item)
    db_session.commit()
    return '', 200


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

