import json

from flask import Flask
from pytest import fixture
from rest.endpoints import (
    create_api,
    default_config,
    register_all_apis,
    schemas_for_paths,
    url_rules_for_path,
)
from rest.handlers import create_schema
from rest.helpers import find
from rest.schema import to_jsonschema
from tests.fixtures import (
    Child,
    Grandchild,
    Level1,
    Level2,
    Level3,
    Parent,
    Root,
    h_data,
    hierarchy_data,
    cyclic_graph,
    hierarchy_graph,
    session,
)
from tests.flask_test_helpers import get_json, patch, post_json
from apitools.datagenerator import DataGenerator


generator = DataGenerator()
path = [Root, Level1, Level2, Level3]


@fixture
def app():
    return Flask(__name__)


def test_schemas_for_paths(cyclic_graph):
    paths = (
        (Parent, Child),
        (Parent, Child, Grandchild),
    )
    config = {
        Parent: {
            'url_name': 'parents',
            'schema': create_schema(Parent, {'exclude': ('children',)})()
        },
        Child: {
            'url_name': 'children',
            'schema': create_schema(
                Child,
                {'exclude': ('parents', 'grandchildren')}
            )()
        },
        Grandchild: {
            'url_name': 'grandchildren',
            'schema': create_schema(Grandchild)()
        }
    }
    parent_hyper_schema = to_jsonschema(config[Parent]['schema'])
    child_hyper_schema = to_jsonschema(config[Child]['schema'])
    grandchild_hyper_schema = to_jsonschema(config[Grandchild]['schema'])
    parent_hyper_schema['links'] = [
        {
            'rel': 'children',
            'href': '/{id}/children',
            'schema_key': Child,
        },
        {
            'rel': 'self',
            'href': '/parents',
            'schema_key': Parent,
        },
    ]
    child_hyper_schema['links'] = [
        {
            'rel': 'grandchildren',
            'href': '/{id}/grandchildren',
            'schema_key': Grandchild,
        },
    ]
    grandchild_hyper_schema['links'] = []
    correct_schemas = {
        Parent: parent_hyper_schema,
        Child: child_hyper_schema,
        Grandchild: grandchild_hyper_schema,
    }
    schemas = schemas_for_paths(paths, config, cyclic_graph)
    x = {m: links_to_tuple(s) for m, s in correct_schemas.iteritems()}
    y = {m: links_to_tuple(s) for m, s in schemas.iteritems()}
    for ss in (correct_schemas, schemas):
        for m, s in ss.iteritems():
            del s['links']
    assert correct_schemas == schemas
    assert y == x


def links_to_tuple(schema):
    new_schema = dict(schema)
    new_schema['links'] = set([tuple(l.items()) for l in schema['links']])
    return new_schema


def test_api_with_schema(session, app):
    roots = [Root]
    c = app.test_client()
    for root in roots:
        apis, schemas = create_api(root, session)
        register_all_apis(app, (schemas, ), (apis, ))
        schema = schemas[root]
        url = find(lambda l: l['rel'] == 'self', schema['links'])['href']
        check_endpoint_(c, url, root, schemas)


def check_dict_contains(d1, d2):
    for k, v in d1.iteritems():
        assert k in d2
        assert d2[k] == v
    


def check_endpoint_(client, url, model, schemas):
    schema = schemas[model]
    items = (generator.random_value(schema) for i in xrange(10))
    ids = {check_post_and_return_id(client, url, item): item for item in items}
    response = client.get(url)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'items' in data
    for d in data['items']:
        check_

    for _id, item in ids.iteritems():
        url = '/'.join(url, _id)
        response = client.get(url)
        assert response.status_code == 200
        data = json.loads(response.data)
    for l in schema['links']:
        for _id, _ in ids.iteritems():
            url = '/'.join(url, _id)
            new_url = ''.join((url, l['href']))
            check_endpoint(client, new_url, l['schema_key'], schemas)
            client.delete(url)


def check_post_and_return_id(client, url, item):
    response = post_json(client, url, item)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'id' in data
    return data['id']


def test_register_handlers(state, hierarchy_graph, hierarchy_data, app):
    config, session = state
    app.debug = True
    client = app.test_client()

    root_apis, from_root_schemas = create_api(Root, session)

    parent_apis, from_parent_schemas = create_api(Parent, session)

    child_apis, from_child_schemas = create_api(Child, session)
    all_schemas = (from_root_schemas, from_parent_schemas, from_child_schemas)
    all_apis = (root_apis, parent_apis, child_apis)
    register_all_apis(app, all_schemas, all_apis)

    check_endpoints(client, '', hierarchy_data,
                    config, hierarchy_graph, Root)
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
    response = client.delete(
        '/parents/' + str(eve_id) + '/children/' + str(cain_id))
    assert response.status_code == 200
    data = get_json(client, '/parents/' + str(eve_id) + '/children')
    assert len(data['items']) == 0


def check_endpoints(client, url, all_data_to_upload, config, graph,
                    start_node):
    url_name = config[start_node]['url_name']
    url = '/'.join([url, url_name])
    s = config[start_node]['collection_serializer']
    d = find(lambda x: isinstance(x[0], start_node), all_data_to_upload)
    item_as_dict = s(d)['items'][0]
    new_url = check_endpoint(client, url, item_as_dict)
    for s in graph.successors_iter(start_node):
        check_endpoints(client, new_url, all_data_to_upload, config, graph, s)
    response = patch(client, new_url, {'name': 'new_name'})
    assert response.status_code == 200
    new_url_parts = new_url.split('/')[:-1] + ['new_name']
    response = client.delete('/'.join(new_url_parts))
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
