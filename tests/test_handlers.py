import json
from functools import partial

from flask import Flask
from pytest import fixture
from rest.handlers import full_query_params, schema_class_for_model, get_item, serialize_item, \
    post_item, deserialize_item, get_collection, serialize_collection, flask_post_wrapper
from rest.query import QueryParams
from tests.flask_test_helpers import get_json, post_json
from tests.test_query import Level2, Level1, Root, Level3, state

level3_item_url = '/roots/root/level1s/level1/level2s/level2/level3s/level3'
level3_collection_url = '/roots/root/level1s/level1/level2s/level2/level3s'

params = (
    (Level3, 'name', 'level3', 'level2_pk', 'name'),
    (Level2, 'name', 'level2', 'level1_pk', 'name'),
    (Level1, 'name', 'level1', 'root_pk', 'name'),
    (Root, 'name', 'root', None, None),
)
kwargs = {
    'level_0_id': 'root',
    'level_1_id': 'level1',
    'level_2_id': 'level2',
    'level_3_id': 'level3',
}

models = (Level3, Level2, Level1, Root)


def empty_params():
    return [QueryParams(*p)._replace(exposed_attr_value=None)
            for p in params]


def test_full_query_params():
    _, full_params = full_query_params(empty_params(), **kwargs)
    assert params == full_params


def test_item_handler(client):
    data = get_json(client, level3_item_url)
    assert data == correct_collection_data()[0]
    response = client.get(level3_collection_url + '/' + 'foo')
    assert response.status_code == 404


def test_collection_handler(client):
    data = get_json(client, level3_collection_url)
    assert 'items' in data
    assert data['items'] == correct_collection_data()


def test_post_handler(client, new_data, wrong_data, url, key):
    response = post_json(client, url, new_data)
    assert response.status_code == 200
    id_ = json.loads(response.data)['id']
    assert id_ == new_data[key]
    assert new_data == get_json(client, url + '/' + id_)
    response = post_json(client, url, wrong_data)
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
            rule='/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s/<level_3_id>',
            endpoint='1',
            view_func=partial(
                    get_item,
                    session,
                    empty_params(),
                    partial(serialize_item, schema_class_for_model(Level3)())
            )
    )
    app.add_url_rule(
            rule='/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s',
            endpoint='2',
            view_func=partial(
                    get_collection,
                    session,
                    empty_params(),
                    partial(serialize_collection, schema_class_for_model(Level3)())
            )
    )
    app.add_url_rule(
            rule='/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s',
            endpoint='3',
            view_func=partial(
                    flask_post_wrapper,
                    partial(
                            post_item,
                            session,
                            empty_params(),
                            partial(deserialize_item, schema_class_for_model(Level3)(), session)
                    )
            )
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
