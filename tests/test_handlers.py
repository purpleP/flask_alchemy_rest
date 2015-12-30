import json
from functools import partial

from flask import Flask
from pytest import fixture
from rest.handlers import full_query_params, get_collection, schema_class_for_model, serialize_collection, \
    serialize_item, get_collection_item, post_flask_wrapper, post_item, deserialize_item
from rest.query import QueryParam
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.flask_test_helpers import get_json, post_json
from tests.test_query import Level2, Level1, ModelBase, Root, Level3

level3_collection_url = '/roots/root/level1s/level1/level2s/level2/level3s'
level3_item_url = '/roots/root/level1s/level1/level2s/level2/level3s/level3'

initial_query_params = (
    QueryParam(
            model=Level3,
            attr_name=None,
            foreign_key_name='level2_pk',
            foreign_key_value=None,
    ),
    QueryParam(
            model=Level2,
            attr_name='name',
            foreign_key_name='level1_pk',
            foreign_key_value=None,
    ),
    QueryParam(
            model=Level1,
            attr_name='name',
            foreign_key_name='root_pk',
            foreign_key_value=None,
    ),
)

correct_full_query_params = (
    QueryParam(
            model=Level3,
            attr_name=None,
            foreign_key_name='level2_pk',
            foreign_key_value='level2',
    ),
    QueryParam(
            model=Level2,
            attr_name='name',
            foreign_key_name='level1_pk',
            foreign_key_value='level1',
    ),
    QueryParam(
            model=Level1,
            attr_name='name',
            foreign_key_name='root_pk',
            foreign_key_value='root',
    ),

)


def test_full_query_params():
    _, full_params = full_query_params(initial_query_params, level_0_id='root', level_1_id='level1',
                                       level_2_id='level2')
    assert correct_full_query_params == full_params


def test_item_handler(client):
    data = get_json(client, level3_item_url)
    assert data == correct_collection_data()[0]
    non_existent_url = level3_collection_url + '/' + 'foo'
    response = client.get(non_existent_url)
    assert response.status_code == 404


def test_collection_handler(client):
    correct_data = correct_collection_data()
    data = get_json(client, level3_collection_url)
    assert 'items' in data
    assert data['items'] == correct_data


def test_post_handler(client):
    new_data = {'name': 'level3_new'}
    response = post_json(client, level3_collection_url, new_data)
    assert response.status_code == 200
    assert json.loads(response.data)['id'] == 'level3_new'
    assert new_data == get_json(client, level3_collection_url + '/' + 'level3_new')
    response = post_json(client, level3_collection_url, {'foo': 'bar'})
    assert response.status_code == 400
    errors_data = json.loads(response.data)
    assert len(errors_data['name']) == 1
    assert errors_data['name'][0] == u'Missing data for required field.'



def items():
    level2 = Level2(name=u'level2')
    level3 = Level3(name=u'level3')
    level2.level3s.append(level3)
    return level2, level3


@fixture
def client():
    app = create_app()
    session = create_session()
    app.add_url_rule(
            rule='/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s',
            endpoint='1',
            view_func=get_handler(get_collection, session, Level3, initial_query_params, serialize_collection),
            methods=['GET']
    )
    app.add_url_rule(
            rule='/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s/<level_3_id>',
            endpoint='2',
            view_func=get_handler(
                    get_collection_item,
                    session,
                    Level3,
                    initial_query_params,
                    serialize_item,
                    primary_key_attr_name='name'
            ),
            methods=['GET']
    )
    app.add_url_rule(
            rule='/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s',
            endpoint='3',
            view_func=post_handler(
                    post_item,
                    session,
                    Level3,
                    initial_query_params,
                    deserialize_item,
                    'name'
            ),
            methods=['POST']
    )
    app.debug = True
    return app.test_client()


def create_app():
    return Flask(__name__)


def create_session():
    engine = create_engine('sqlite:///:memory:', echo=False, convert_unicode=True)
    session = sessionmaker(autocommit=False,
                           autoflush=False,
                           bind=engine)()
    ModelBase.metadata.create_all(engine)
    root = Root(name='root')
    l1 = Level1(name='level1')
    level2, level3 = items()
    l1.level2s.append(level2)
    root.level1s.append(l1)
    session.add(root)
    session.commit()
    return session


def get_handler(actual_handler, session, model, params, schema_based_serializer, **kwargs):
    schema = schema_class_for_model(model)()
    serializer = partial(schema_based_serializer, schema)
    return partial(actual_handler, session, params, serializer, **kwargs)


def post_handler(actual_handler, session, model, params, schema_based_deserializer, url_key, **kwargs):
    schema = schema_class_for_model(model)()
    deserializer = partial(schema_based_deserializer, schema, session)
    actual_poster = partial(actual_handler, session, params, deserializer, url_key,  **kwargs)
    return partial(post_flask_wrapper, actual_poster)




def correct_collection_data():
    return [
        {
            'name': 'level3'
        },
    ]
