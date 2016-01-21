import json
from functools import partial

from flask import Flask
from pytest import fixture
from rest.handlers import schema_class_for_model, get_item, \
    serialize_item, \
    post_item, deserialize_item, get_collection, serialize_collection, \
    post_item_many_to_many, delete_item, create_handler, post_handler
from tests.fixtures import Level3, state, \
    level3_item_url, level3_collection_url, level3_item_rule, \
    level3_collection_rule, paths, Root, Child, Parent, cycled_data
from tests.flask_test_helpers import get_json, post_json

kwargs = {
    'level_0_id': 'root',
    'level_1_id': 'level1',
    'level_2_id': 'level2',
    'level_3_id': 'level3',
}


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
    response = post_json(client, '/roots', new_data)
    assert response.status_code == 200
    assert id_ == 'bar'
    response = client.delete(level3_collection_url + '/' + id_)
    assert response.status_code == 200
    assert get_json(client, level3_collection_url)['items'] == [
        {'name': 'level3'}]
    new_data['level1s'] = []
    assert new_data == get_json(client, '/roots/bar')
    response = post_json(client, level3_collection_url, wrong_data)
    assert response.status_code == 400
    errors_data = json.loads(response.data)
    assert len(errors_data['name']) == 1
    assert errors_data['name'][0] == u'Missing data for required field.'


def test_post_many_to_many(client_session):
    c, s = client_session
    adam_id = s.query(Parent.id).filter_by(name='Adam').one().id
    cain_id = s.query(Child.id).filter_by(name='Cain').one().id
    response = post_json(c, '/parents/' + str(adam_id) + '/' + 'children',
                         {'id': cain_id})
    assert response.status_code == 200
    adam = s.query(Parent).filter_by(name='Adam').one()
    assert len(adam.children) == 1
    assert adam.children[0].name == 'Cain'


@fixture
def client_session():
    app = create_app()
    session, data = state()
    app.debug = True
    cycled_paths = [
        [(Parent, 'id')],
        [(Child, 'id'), (Parent, 'id')]
    ]
    adam, eve, cain, abel = cycled_data()
    session.add(adam)
    session.add(eve)
    session.add(cain)
    session.commit()

    app.add_url_rule(
        rule='/parents/<level_0_id>',
        endpoint='/parents_GET',
        view_func=create_handler(
            partial(
                get_item,
                session,
                cycled_paths[0],
                partial(serialize_item, schema_class_for_model(Parent)())
            )
        ),
        methods=['GET']
    )
    app.add_url_rule(
        rule='/parents/<level_0_id>/children',
        endpoint='/parents_post',
        view_func=post_handler(
            partial(
                post_item_many_to_many,
                session,
                cycled_paths[1],
                'children'
            )
        ),
        methods=['POST']
    )
    app.add_url_rule(
        rule='/roots/<level_0_id>',
        endpoint='/roots_item_get',
        view_func=create_handler(
            partial(
                get_item,
                session,
                paths()[0],
                partial(serialize_item, schema_class_for_model(Root)())
            )
        )
    )
    app.add_url_rule(
        rule='/roots',
        endpoint='/roots_post',
        view_func=post_handler(
            partial(
                post_item,
                session,
                paths()[0],
                None,
                partial(deserialize_item, schema_class_for_model(Root)(), session)
            )
        ),
        methods=['POST']
    )
    app.add_url_rule(
        rule=level3_item_rule,
        endpoint='1',
        view_func=create_handler(
            partial(
                get_item,
                session,
                paths()[-1],
                partial(serialize_item, schema_class_for_model(Level3)())
            )
        ),
        methods=['GET']
    )
    app.add_url_rule(
        rule=level3_collection_rule,
        endpoint='2',
        view_func=create_handler(
            partial(
                get_collection,
                session,
                paths()[-1],
                partial(serialize_collection, schema_class_for_model(Level3)())
            )
        ),
        methods=['GET']
    )
    app.add_url_rule(
        rule=level3_collection_rule,
        endpoint='3',
        view_func=post_handler(
            partial(
                post_item,
                session,
                paths()[-1],
                'level3s',
                partial(
                    deserialize_item,
                    schema_class_for_model(Level3)(),
                    session
                )
            )
        ),
        methods=['POST']
    )
    app.add_url_rule(
        rule=level3_item_rule,
        endpoint='4',
        view_func=create_handler(
            partial(
                delete_item,
                session,
                paths()[-1],
            )
        ),
        methods=['DELETE']
    )

    return app.test_client(), session


@fixture
def client():
    c, s = client_session()
    return c


def create_app():
    return Flask(__name__)


def correct_collection_data():
    return [
        {
            'name': 'level3'
        },
    ]
