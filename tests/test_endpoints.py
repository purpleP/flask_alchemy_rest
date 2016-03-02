import json

from flask import Flask
from functools import reduce
from itertools import permutations
from pytest import fixture
import pytest
from rest.endpoints import (
    create_api,
    default_config,
    register_all_apis,
    schemas_for_paths,
    url_rules_for_path,
)
from rest.helpers import merge, compose, identity, find
from rest.handlers import create_schema
from rest.decorators import without_relations
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
    cyclic_graph,
    hierarchy_graph,
    session,
)
from tests.flask_test_helpers import post_json


@fixture
def app():
    app = Flask(__name__)
    app.debug = True
    return app


def parent_child_config_decorator(config):
    config[Parent]['exposed_attr'] = 'name'
    config[Parent]['exposed_attr_type'] = ''
    config[Child]['exposed_attr'] = 'name'
    config[Child]['exposed_attr_type'] = ''
    config[Grandchild]['exposed_attr'] = 'name'
    config[Grandchild]['exposed_attr_type'] = ''
    return config


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


def api(session, app, roots_with_decs):
    dh = DataHolder(session)
    apis_with_schemas = [create_api(
        root,
        session,
        graph_decorator=compose(
            dh.extract_graph,
            decorators.get('graph', identity)
        ),
        config_decorator=compose(
            dh.remove_relations,
            decorators.get('config', identity)
        )
    )
                         for root, decorators in roots_with_decs]
    apiss = (apis for apis, schemas in apis_with_schemas)
    schemas = (schemas for apiss, schemas in apis_with_schemas)
    complete_schemas = reduce(merge, schemas, {})

    for s in complete_schemas.values():
        s['properties']['name']['pattern'] = '[a-z]{1,10}$'
    register_all_apis(app, complete_schemas, apiss)
    return complete_schemas, app.test_client()


@pytest.mark.parametrize('schemas,client', [
    api(
        session(),
        app(),
        (
                (Root, {}),
        )
    ),
    api(
        session(),
        app(),
        (
                (Parent, {'config': parent_child_config_decorator}),
                (Child, {'config': parent_child_config_decorator})
        )
    )
])
def test_api(schemas, client):
    check_endpoint(client, '', schemas, base_name='base')


def dict_contains(d1, d2):
    for k, v in d2.iteritems():
        if k not in d1:
            return False
        else:
            if d1[k] != v:
                return False
    return True


def is_many_to_many(schemas, link, model):
    return model in [
        l['schema_key'] for l in schemas[link['schema_key']]['links']
        ]


def check_endpoint(client, url, schemas, model=None, base_name=None):
    # TODO check PATCH
    # TODO refactor to be able to check many-to-many relationships
    if model:
        schema = schemas[model]

        links = (l for l in schema['links'] if l['rel'] != 'self')
        simple_links = [l for l in links
                        if not is_many_to_many(schemas, l, model)]
        check_empty_collection(client, url)

        upload_count = 2
        ids_to_items = upload_random_data(
            client,
            upload_count,
            schema,
            url,
            '_'.join((base_name, model.__name__.lower()))
        )
        check_if_uploaded(client, ids_to_items, url)
    else:
        import pdb
        pdb.set_trace()
        links = [l for s in schemas.values() for l in s['links']
                 if l['rel'] == 'self']
        simple_links = links
        ids_to_items = {'': {'name': base_name}}

    next_level_data = [(
        l,
        {_id: check_endpoint(
            client=client,
            url=''.join((url, l['href'].format(id=_id))),
            schemas=schemas,
            model=l['schema_key'],
            base_name=item['name']
        )
         for _id, item in ids_to_items.iteritems()}
    )
        for l in simple_links]

    link_pairs = [
        (l1, l2) for l1, l2 in permutations(simple_links, 2)
        if l2['schema_key'] in [
            l['schema_key'] for l
            in schemas[l1['schema_key']]['links']
        ]
    ]

    many_to_many_data = [
        (
            lp1, find(lambda ld: ld[0] == lp1, next_level_data)[1],
            lp2, find(lambda ld: ld[0] == lp2, next_level_data)[1],
        )
        for lp1, lp2 in link_pairs]

    return ids_to_items


def check_if_uploaded(client, items, url):
    response = client.get(url)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'items' in data
    assert len(data['items']) == len(items)
    is_uploaded = {_id: any([dict_contains(ri, i) for ri in data['items']])
                   for _id, i in items.iteritems()}
    assert all(is_uploaded.values()) is True
    responses = [(item, client.get('/'.join((url, str(_id)))))
                 for _id, item in items.iteritems()]
    is_oks = [r.status_code == 200 for i, r in responses]
    assert all(is_oks)
    response_contains_item = [dict_contains(json.loads(r.data), i)
                              for i, r in responses]
    assert all(response_contains_item)


def upload_random_data(client, items_to_upload_count, schema, url, base_name):
    items = []
    while (len(items) != items_to_upload_count):
        random_object = object_(schema)
        if random_object not in items:
            items.append(random_object)

    if base_name:
        for item in items:
            item['name'] = '_'.join((base_name, item['name']))
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


def test_url_for_path(session, cyclic_graph):
    path = [Parent, Child, Grandchild]
    config = parent_child_config_decorator(default_config(path, session))
    collection_url_rule, item_url_rule = url_rules_for_path(
        path,
        config,
        cyclic_graph
    )
    correct_collection_url_rule = (
        '/parents/<level_0_id>/'
        'children/<level_1_id>/grandchildren'
    )
    correct_item_url_rule = correct_collection_url_rule + '/<level_2_id>'
    assert collection_url_rule == correct_collection_url_rule
    assert item_url_rule == correct_item_url_rule
