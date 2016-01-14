import json
from functools import partial

from flask import Flask
from pytest import fixture
from rest.handlers import schema_class_for_model, get_item, \
    serialize_item, \
    post_item, deserialize_item, get_collection, serialize_collection, \
    flask_post_wrapper
from rest.query import QueryParams
from tests.fixtures import Root, Level1, Level2, Level3, state, params, \
    level3_item_url, level3_collection_url, level3_item_rule, \
    level3_collection_rule
from tests.flask_test_helpers import get_json, post_json

kwargs = {
    'level_0_id': 'root',
    'level_1_id': 'level1',
    'level_2_id': 'level2',
    'level_3_id': 'level3',
}

models = (Level3, Level2, Level1, Root)


def params_as_namedtuple():
    return [QueryParams(*p) for p in params()]


def test_item_handler(client):
    response = client.get(level3_item_url)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == correct_collection_data()[0]
    response = client.get(level3_collection_url + '/' + 'foo')
    assert response.status_code == 404


def test_collection_handler(client):
    response = client.get(level3_collection_url)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'items' in data
    assert data['items'] == correct_collection_data()


def test_post_handler(client):
    new_data = {'name': 'bar'}
    wrong_data = {'foo': 'bar'}
    response = post_json(client, level3_collection_url, new_data)
    assert response.status_code == 200
    id_ = json.loads(response.data)['id']
    assert id_ == 'bar'
    assert new_data == get_json(client, level3_collection_url + '/' + id_)
    response = post_json(client, level3_collection_url, wrong_data)
    assert response.status_code == 400
    errors_data = json.loads(response.data)
    assert len(errors_data['name']) == 1
    assert errors_data['name'][0] == u'Missing data for required field.'


@fixture
def client():
    app = create_app()
    session, data = state()
    app.debug = True
    app.add_url_rule(
            rule=level3_item_rule,
            endpoint='1',
            view_func=partial(
                    get_item,
                    session,
                    params_as_namedtuple(),
                    partial(serialize_item, schema_class_for_model(Level3)())
            )
    )
    app.add_url_rule(
            rule=level3_collection_rule,
            endpoint='2',
            view_func=partial(
                    get_collection,
                    session,
                    params_as_namedtuple(),
                    partial(serialize_collection,
                            schema_class_for_model(Level3)())
            )
    )
    app.add_url_rule(
            rule=level3_collection_rule,
            endpoint='3',
            view_func=partial(
                    flask_post_wrapper,
                    partial(
                            post_item,
                            session,
                            params_as_namedtuple(),
                            partial(deserialize_item,
                                    schema_class_for_model(Level3)(), session)
                    )
            ),
            methods=['POST']
    )

    return app.test_client()


def create_app():
    return Flask(__name__)


def correct_collection_data():
    return [
        {
            'name': 'level3'
        },
    ]
