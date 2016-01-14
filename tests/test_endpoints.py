import networkx as nx
from flask import Flask
from pytest import fixture
from rest.endpoints import params_from_path, urls_for_path, default_config, \
    register_handlers
from rest.hierarchy_traverser import sublists
from tests.fixtures import Root, Level1, Level2, Level3, params, state, \
    level3_item_url

g = nx.DiGraph()
g.add_edge(Root, Root, fk_attr=None, linked_attr=None)
g.add_edge(Root, Level1, linked_attr='name', fk_attr='root_pk')
g.add_edge(Level1, Level2, linked_attr='name', fk_attr='level1_pk')
g.add_edge(Level2, Level3, linked_attr='name', fk_attr='level2_pk')
path = [Root, Level1, Level2, Level3]


def test_register_handlers(config):
    app = Flask(__name__)
    client = app.test_client()
    session, _ = state()
    register_handlers(
            graph=g,
            root=Root,
            config=config,
            db_session=session,
            app=app
    )
    urls_parts = level3_item_url.split('/')
    urls = ['/'.join(sl) for sl in sublists(urls_parts)][1:]
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200


def test_params_from_path(config):
    p = params_from_path(g, path, config)
    assert p == params()


def test_default_config(config):
    pass
    # assert config == default_config(path)


def test_url_for_path(config):
    collection_url, item_url = urls_for_path(path, config)
    correct_collection_url = '/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s'
    correct_item_url = '/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s/<level_3_id>'
    assert collection_url == correct_collection_url
    assert item_url == correct_item_url


@fixture
def config():
    return default_config(path)

