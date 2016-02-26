import json

from flask import Flask
from functools import reduce
from pytest import fixture
import pytest
from rest.endpoints import (
    create_api,
    default_config,
    register_all_apis,
    schemas_for_paths,
    url_rules_for_path,
)
from rest.helpers import merge
from rest.handlers import create_schema
from rest.decorators import without_relations
from rest.helpers import find
from rest.generators import object_
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


class DataHolder(object):
    def __init__(self, session):
        self.graph = None
        self.session = session

    def extract_graph(self, graph):
        self.graph = graph
        return graph

    def remove_relations(self, config):
        return without_relations(self.session, self.graph, config)


def api(session, app, roots):
    dh = DataHolder(session)
    apis_with_schemas = [create_api(
        root,
        session,
        graph_decorator=dh.extract_graph,
        config_decorator=dh.remove_relations
    )
        for root in roots]
    apis = (apis for apis, schemas in apis_with_schemas)
    schemas = (schemas for apis, schemas in apis_with_schemas)
    complete_schemas = reduce(merge, schemas, {})

    for s in complete_schemas.values():
        s['properties']['name']['pattern'] = '[a-z]{1,10}$'
    register_all_apis(app, complete_schemas, apis)
    return complete_schemas, app.test_client()


@pytest.mark.parametrize('schemas,client', [
    api(session(), app(), (Root,)),
    # api(session(), app(), (Parent, Child))
])
def test_api(schemas, client):
        check_endpoint(client, '', schemas)


def dict_contains(d1, d2):
    for k, v in d2.iteritems():
        if k not in d1:
            return False
        else:
            if d1[k] != v:
                return False
    return True


def check_endpoint(client, url, schemas, model=None):
    # TODO check PATCH
    # TODO refactor to be able to check many-to-many relationships
    if model:
        schema = schemas[model]

        def is_many_to_many(link):
            return model in [
                l['schema_key'] for l in schemas[link['schema_key']]['links']
            ]
        links = (l for l in schema['links'] if l['rel'] != 'self')
        simple_links = (l for l in links if not is_many_to_many(l))
        many_to_many_links = (l for l in links if is_many_to_many(l))
        check_empty_collection(client, url)

        upload_count = 2
        ids_to_items = upload_random_data(client, upload_count, schema, url)
        check_if_uploaded(client, ids_to_items, url)
    else:
        links = [l for s in schemas.values() for l in s['links']
                 if l['rel'] == 'self']
        simple_links = links
        ids_to_items = {'': None}
        many_to_many_links = ()

    next_level_data = [(
        l,
        {_id: check_endpoint(
                client,
                ''.join((url, l['href'].format(id=_id))),
                schemas,
                l['schema_key']
            )
         for _id in ids_to_items.keys()}
    )
        for l in simple_links]
    print(next_level_data)

    return many_to_many_links, ids_to_items

    # for l, urls in circular_links_by_ids:
        # for url, data in urls.iteritems():
            # for _id in data.ids:
                # item_url = '/'.join((url, _ids))
                # client.delete(item_url)


def check_if_uploaded(client, items, url):
    response = client.get(url)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'items' in data
    assert len(data['items']) == len(items)
    is_uploaded = {_id: any([dict_contains(ri, i) for ri in data['items']])
                   for _id, i in items.iteritems()}
    assert all(is_uploaded.values()) is True
    responses = [(item, client.get('/'.join((url, _id))))
                 for _id, item in items.iteritems()]
    is_oks = [r.status_code == 200 for i, r in responses]
    assert all(is_oks)
    response_contains_item = [dict_contains(json.loads(r.data), i)
                              for i, r in responses]
    assert all(response_contains_item)


def upload_random_data(client, items_to_upload_count, schema, url):
    items = []
    while (len(items) != items_to_upload_count):
        random_object = object_(schema)
        if random_object not in items:
            items.append(random_object)
    ids = {check_post_and_return_id(client, url, item): item for item in items}
    return ids


def check_empty_collection(client, url):
    response = client.get(url)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'items' in data
    assert len(data['items']) == 0


def check_post_and_return_id(client, url, item):
    response = post_json(client, url, item)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'id' in data
    return data['id']


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
