import json

from functools import partial
from rest.helpers import compose_wrappers, add_item

from flask import jsonify, request
from marshmallow_sqlalchemy import ModelSchema
from sqlalchemy.orm.exc import NoResultFound
from six import iteritems

NO_SUCH_ITEM_MESSAGE = 'No such item resourse'
NO_SUCH_PARENT_MESSAGE = 'No such parent resource'
NO_SUCH_RESOURCE_MESSAGE = 'No such resource'


def get_collection(db_session, query, serializer, *keys, **kwargs):
    spec = kwargs.get('spec', lambda x: x)
    from_ = kwargs.get('from_', None)
    count = kwargs.get('count', None)
    page_num = kwargs.get('page_num', None)
    page_size = kwargs.get('page_size', None)
    cq = query(session=db_session, keys=keys)
    scq = spec(cq)
    if page_num is not None and page_size is not None:
        count = scq.count()
        offset = (page_num - 1) * page_size
        q = scq.offset(offset).limit(page_size)
        items = q.all()
        output = serializer(items)
        output['total'] = count
        output['count'] = len(items)
    else:
        output = serializer(scq.all())
    return jsonify(output)


def get_item(db_session, query, serializer, *keys):
    item_query = query(session=db_session, keys=keys)
    try:
        item = item_query.one()
        return jsonify(serializer(item))
    except NoResultFound:
        return NO_SUCH_RESOURCE_MESSAGE, 404


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
    add_item(parent, rel_attr_name, item)


def post_item_many_to_many(db_session, item_query, parent_query, rel_attr_name,
                           *keys, **kwargs):
    try:
        _id = kwargs.pop('data')['id']
        item = item_query(session=db_session, keys=(_id,)).one()
    except NoResultFound:
        return NO_SUCH_ITEM_MESSAGE, 404
    else:
        try:
            parent = parent_query(session=db_session, keys=keys).one()
            db_session.add(parent)
            add_item(parent, rel_attr_name, item)
            db_session.commit()
            return '', 200
        except NoResultFound:
            return NO_SUCH_PARENT_MESSAGE, 404


def delete_item(db_session, query, *keys):
    try:
        db_session.delete(query(session=db_session, keys=keys).one())
        db_session.commit()
        return '', 200
    except NoResultFound:
        return NO_SUCH_RESOURCE_MESSAGE, 404


def delete_many_to_many(db_session, item_query, parent_query,
                        rel_attr_name, *keys):
    try:
        item = item_query(session=db_session, keys=keys[0:1]).one()
    except NoResultFound:
        return NO_SUCH_ITEM_MESSAGE, 404
    else:
        try:
            parent = parent_query(session=db_session, keys=keys[1:]).one()
            db_session.add(parent)
            getattr(parent, rel_attr_name).remove(item)
            db_session.commit()
            return '', 200
        except NoResultFound:
            return NO_SUCH_PARENT_MESSAGE, 404


def patch_item(db_session, query, *keys, **kwargs):
    item_query = query(session=db_session, keys=keys)
    try:
        item = item_query.one()
        db_session.add(item)
        for attr, new_value in iteritems(kwargs.pop('data')):
            setattr(item, attr, new_value)
        db_session.commit()
        return '', 200
    except NoResultFound:
        return NO_SUCH_RESOURCE_MESSAGE, 404


def schemas_handler(schemas):
    return jsonify(schemas)


def keys_from_kwargs(**kwargs):
    return tuple((kwargs[key] for key in sorted(kwargs.keys(), reverse=True)))


def create_handler(handler):
    return wrap(handler, keys_wrapper)


def wrap(f, wrapper):
    def z(*args, **kwargs):
        args, kwargs = wrapper(*args, **kwargs)
        return f(*args, **kwargs)
    return z


def keys_wrapper(*args, **kwargs):
    return keys_from_kwargs(**kwargs), {}


def spec_wrapper(specs, *args, **kwargs):
    spec_as_str = request.args.get('spec', None)
    if spec_as_str:
        spec_dict = json.loads(spec_as_str)
        try:
            spec = partial(specs[spec_dict['name']], *spec_dict['args'])
            kwargs['spec'] = spec
        except KeyError:
            return 'No such spec for this resource', 400
    return args, kwargs


def request_data_wrapper(*args, **kwargs):
    kwargs['data'] = json.loads(request.data.decode('utf-8'))
    return args, kwargs


def get_handler(handler, specs={}):
    w = compose_wrappers(
        partial(spec_wrapper, specs),
        cursor_wrapper,
        keys_wrapper,
    )
    return wrap(handler, w)


def data_handler(handler):
    w = compose_wrappers(request_data_wrapper, keys_wrapper)
    return wrap(handler, w)


def cursor_wrapper(*args, **kwargs):
    page_num = request.args.get('page', None)
    page_size = request.args.get('size', None)
    kwargs['page_num'] = int(page_num) if page_num else None
    kwargs['page_size'] = int(page_size) if page_size else None
    return args, kwargs


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


def create_schema(model_class, meta_dict={}):
    meta_dict['model'] = model_class
    schema_meta = type('Meta', (object,), meta_dict)
    return type(
            model_class.__name__ + 'Schema',
            (ModelSchema,),
            {'Meta': schema_meta}
    )
