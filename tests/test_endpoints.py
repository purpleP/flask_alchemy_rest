import json

from flask import Flask
from pytest import fixture
from rest.endpoints import url_rules_for_path, default_config, \
    reversed_paths, create_api
from rest.introspect import find
from tests.fixtures import Root, Level1, Level2, Level3, models_graphs, \
    Parent, Child, session, hierarchy_data
from tests.flask_test_helpers import post_json, get_json

path = [Root, Level1, Level2, Level3]


def test_register_handlers(state):
    config, session = state
    app = Flask(__name__)
    app.debug = True
    client = app.test_client()
    hierarchy, with_cycles = models_graphs()

    create_api(Root, session, app)
    create_api(Parent, session, app)
    create_api(Child, session, app)

    all_data_to_upload = hierarchy_data()
    check_endpoints(client, '', all_data_to_upload, config, hierarchy, Root)
    response = post_json(client, '/parents', {'name': 'Adam'})
    assert response.status_code == 200
    adam_id = json.loads(response.data)['id']
    response = post_json(client, '/parents', {'name': 'Eve'})
    assert response.status_code == 200
    eve_id = json.loads(response.data)['id']
    cain = {'name': 'Cain'}
    response = post_json(client, '/children', cain)
    assert response.status_code == 200
    cain_id = json.loads(response.data)['id']
    response = post_json(client, '/parents/' + str(adam_id) + '/' + 'children',
                         {'id': cain_id})
    assert response.status_code == 200
    response = client.get('/parents/' + str(adam_id))
    assert response.status_code == 200
    children = json.loads(response.data)['children']
    assert len(children) == 1
    assert children[0] == cain_id
    response = post_json(client, '/parents/' + str(eve_id) + '/' + 'children',
                         {'id': cain_id})
    assert response.status_code == 200
    response = client.get('/parents/' + str(eve_id))
    assert response.status_code == 200
    children = json.loads(response.data)['children']
    assert len(children) == 1
    assert children[0] == cain_id
    response = client.get('/'.join(('/children', str(cain_id))))
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['parents'] == [adam_id, eve_id]



def check_endpoints(client, url, all_data_to_upload, config, graph, start_node):
    url_name = config[start_node]['url_name']
    url = '/'.join([url, url_name])
    s = config[start_node]['collection_serializer']
    d = find(lambda x: isinstance(x[0], start_node), all_data_to_upload)
    item_as_dict = s(d)[0]
    new_url = check_endpoint(client, url, item_as_dict)
    for s in graph.successors_iter(start_node):
        check_endpoints(client, new_url, all_data_to_upload, config, graph, s)
    response = client.delete(new_url)
    assert response.status_code == 200
    data = get_json(client, url)
    assert len(data['items']) == 0



def check_endpoint(client, collection_url, item_as_dict):
    check_collection_is_empty(client, collection_url)
    assert client.get(collection_url + '/' + 'zzz').status_code == 404
    response = post_json(client, collection_url, item_as_dict)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'id' in data
    _id = data['id']
    response = client.get(collection_url)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'items' in data
    assert len(data['items']) == 1
    assert data['items'][0] == item_as_dict
    item_url = collection_url + '/' + str(_id)
    response = client.get(item_url)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == item_as_dict
    return item_url


def check_collection_is_empty(client, url):
    response = client.get(url)
    assert response.status_code == 200
    assert 'items' in response.data
    assert len(json.loads(response.data)['items']) == 0


def test_default_config(config):
    pass
    # assert config == default_config(path)


def test_reversed_paths():
    path = [Parent, Child]
    correct_output = [
        (Child, 'id'),
        (Parent, 'id'),
    ]
    config = {
        Parent: {
            'exposed_attr': 'id',
        },
        Child: {
            'exposed_attr': 'id',
        },
    }
    assert correct_output == reversed_paths(path, config)


def test_url_for_path(config):
    collection_url, item_url = url_rules_for_path(path, config)
    correct_collection_url = '/roots/<level_0_id>/level1s/' \
                             '<level_1_id>/level2s/<level_2_id>/level3s'
    correct_item_url = '/roots/<level_0_id>/level1s/' \
                       '<level_1_id>/level2s/<level_2_id>/level3s/<level_3_id>'
    assert collection_url == correct_collection_url
    assert item_url == correct_item_url
    correct_item_url = '/parents/<int:level_0_id>'
    path_ = [Parent]
    _, item_url = url_rules_for_path(path_, default_config(path_))
    assert correct_item_url == item_url


@fixture
def config():
    return state()[0]


@fixture
def state():
    s = session()
    return default_config(path, s), s
