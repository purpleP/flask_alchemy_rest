import json
from functools import partial
from itertools import chain

from flask import Flask
from pytest import fixture
from rest.handlers import schema_maker, get_item, \
    serialize_item, get_handler, \
    post_item, deserialize_item, get_collection, serialize_collection, \
    post_item_many_to_many, delete_item, create_handler, post_handler
from tests.fixtures import Level3, state, \
    level3_item_url, level3_collection_url, level3_item_rule, \
    level3_collection_rule, paths, Root, Child, Parent, cycled_data, session, \
    Level1, Level2
from tests.flask_test_helpers import get_json, post_json


def test_collection_handler(session_, data_, client):
    s, d, app = session_data_app
    c = app.test_client()

    app.add_url_rule(
            rule=level3_collection_rule,
            endpoint='2',
            view_func=get_handler(
                    partial(
                            get_collection,
                            s,
                            paths()[-1],
                            partial(serialize_collection,
                                    schema_maker(Level3)())
                    ),
                    {'by_name': by_name_spec}
            ),
            methods=['GET']
    )
    root, l1, l2, l3 = d
    l1.level2s.append(l2)
    root.level1s.append(l1)
    s.add(root)
    s.commit()
    collection_url = '/' + '/'.join(url_parts(d, url_names)[:-1])

    response = c.get(collection_url)
    assert response.status_code == 200
    assert json.loads(response.data) == {'items': []}
    l2.level3s.append(l3)
    s.commit()
    response = c.get(collection_url)
    assert response.status_code == 200
    assert json.loads(response.data) == {'items': [{'name': 'level3_1'}]}
    response = search(c, collection_url, 'level3')
    assert response.status_code == 200
    assert len(json.loads(response.data)['items']) == 0

    l2.level3s.append(Level3(name='level3'))
    s.commit()
    response = search(c, collection_url, 'level3')
    assert json.loads(response.data)['items'] == [{'name': 'level3'}]



def test_item_handler(session_data_app):
    s, d, app = session_data_app
    c = app.test_client()
    root, l1, l2, l3 = d
    app.add_url_rule(
            rule=level3_item_rule,
            endpoint='1',
            view_func=create_handler(
                    partial(
                            get_item,
                            s,
                            paths()[-1],
                            partial(serialize_item, schema_maker(Level3)())
                    )
            ),
            methods=['GET']
    )
    url = '/' + '/'.join(url_parts(d, url_names))
    check_404_with_no_data(c, url)
    s.add(root)
    l1.level2s.append(l2)
    root.level1s.append(l1)
    s.commit()
    check_404_with_no_data(c, url)
    s.add(root)
    l2.level3s.append(l3)
    s.commit()
    response = c.get(url)
    assert response.status_code == 200
    assert json.loads(response.data) == {'name': 'level3_1'}


def test_post_item(session_data_app):
    s, d, app = session_data_app
    c = app.test_client()
    app.add_url_rule(
            rule='/roots',
            endpoint='/roots_post',
            view_func=post_handler(
                    partial(
                            post_item,
                            s,
                            paths()[0],
                            None,
                            partial(deserialize_item,
                                    schema_maker(Root)(), s)
                    )
            ),
            methods=['POST']
    )
    response = post_json(c, '/roots', {'name': 'root'})
    assert response.status_code == 200
    roots = s.query(Root).filter_by(name='root').all()
    assert len(roots) == 1
    response = post_json(c, '/roots/root/level1s', {'name': 'level1'})
    assert response.status_code == 200
    level1s = s.query(Level1).filter(Root == roots[0])
    assert len(level1s) == 1




def url_parts(d, url_names):
    url_parts = list(chain(*(zip(url_names, map(lambda x: x.name, d)))))
    return url_parts


def check_404_with_no_data(c, url):
    response = c.get(url)
    assert response.status_code == 404


url_names = ['roots', 'level1s', 'level2s', 'level3s']


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
    items = get_json(client, level3_collection_url)['items']
    assert items == correct_collection_data()
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


def by_name_spec(name, query):
    return query.filter_by(name=name)


@fixture
def session_data_app():
    app = create_app()
    app.debug = True
    s = session()
    return s, data(), app


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
    session.add(Level3(name='baz'))
    session.commit()

    app.add_url_rule(
            rule='/parents/<level_0_id>',
            endpoint='/parents_GET',
            view_func=create_handler(
                    partial(
                            get_item,
                            session,
                            cycled_paths[0],
                            partial(serialize_item, schema_maker(Parent)())
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
                            partial(serialize_item, schema_maker(Root)())
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
                            partial(deserialize_item,
                                    schema_maker(Root)(), session)
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
                            partial(serialize_item, schema_maker(Level3)())
                    )
            ),
            methods=['GET']
    )
    app.add_url_rule(
            rule=level3_collection_rule,
            endpoint='2',
            view_func=get_handler(
                    partial(
                            get_collection,
                            session,
                            paths()[-1],
                            partial(serialize_collection,
                                    schema_maker(Level3)())
                    ),
                    {'by_name': by_name_spec}
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
                                    schema_maker(Level3)(),
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


def search(client, url, name):
    spec_dict = {'name': 'by_name', 'args': (name,)}
    q_dict = {'spec': json.dumps(spec_dict)}
    return client.get(url, query_string=q_dict)


kwargs = {
    'level_0_id': 'root',
    'level_1_id': 'level1',
    'level_2_id': 'level2',
    'level_3_id': 'level3',
}


def data():
    root = Root(name='root1')
    l1 = Level1(name='level1_1')
    l2 = Level2(name='level2_1')
    l3 = Level3(name='level3_1')
    return root, l1, l2, l3
