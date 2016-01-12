import networkx as nx
from pytest import fixture
from rest.endpoints import params_from_path, urls_for_path, default_config, register_handlers
from rest.hierarchy_traverser import RelationshipInfo, sublists
from rest.query import QueryParam
from tests.test_handlers import create_app, create_session, level3_item_url
from tests.test_query import Level3, Level2, Level1, Root

g = nx.DiGraph()
g.add_edge(Root, Level1, rel=RelationshipInfo('name', 'root_pk'))
g.add_edge(Level1, Level2, rel=RelationshipInfo('name', 'level1_pk'))
g.add_edge(Level2, Level3, rel=RelationshipInfo('name', 'level2_pk'))
path = [Root, Level1, Level2, Level3]


def test_register_handlers(config):
    app = create_app()
    client = app.test_client()
    session = create_session()
    register_handlers(
            graph=g,
            root=Root,
            config=config,
            db_session=session,
            app=app
    )
    urls_parts = level3_item_url.split('/')
    urls = ['/'.join(sl) for sl in sublists(urls_parts)]
    for url in urls:
        response = client.get(url)
        assert response.status == 200


def test_params_from_path():
    correct_params = level_3_params()
    p = params_from_path(g, path)
    assert p == correct_params


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


@fixture
def level_3_params():
    correct_params = (
        QueryParam(
                model=Level3,
                attr_name=None,
                foreign_key_name='level2_pk',
                foreign_key_value=None
        ),
        QueryParam(
                model=Level2,
                attr_name='name',
                foreign_key_name='level1_pk',
                foreign_key_value=None
        ),
        QueryParam(
                model=Level1,
                attr_name='name',
                foreign_key_name='root_pk',
                foreign_key_value=None
        )
    )
    return correct_params


@fixture
def level_2_params():
    correct_params = (
        QueryParam(
                model=Level2,
                attr_name=None,
                foreign_key_name='level1_pk',
                foreign_key_value=None
        ),
        QueryParam(
                model=Level1,
                attr_name='name',
                foreign_key_name='root_pk',
                foreign_key_value=None
        ),
    )
    return correct_params
