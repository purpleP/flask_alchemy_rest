import networkx as nx
from pytest import fixture
from rest.endpoints import params_from_path, urls_for_path, config_name_provider
from rest.handlers import serialize_item, default_serializer_or_deserializer, serialize_collection, deserialize_item
from rest.hierarchy_traverser import RelationshipInfo
from rest.query import QueryParam
from tests.test_query import Level3, Level2, Level1, Root

g = nx.DiGraph()
g.add_edge(Root, Level1, rel=RelationshipInfo('name', 'root_pk'))
g.add_edge(Level1, Level2, rel=RelationshipInfo('name', 'level1_pk'))
g.add_edge(Level2, Level3, rel=RelationshipInfo('name', 'level2_pk'))
path = [Root, Level1, Level2, Level3]


config = {
    Root: {
        'url_name': 'roots',
        'item_serializer': default_serializer_or_deserializer(serialize_item, Root, db_session=None),
        'collection_serializer': default_serializer_or_deserializer(serialize_collection, Root, db_session=None),
        'item_deserializer': default_serializer_or_deserializer(deserialize_item, Root, db_session=None),
        'attr_to_use_in_url': 'name'
    },
    Level1: {
        'url_name': 'level1s',
        'item_serializer': default_serializer_or_deserializer(serialize_item, Root, db_session=None),
        'collection_serializer': default_serializer_or_deserializer(serialize_collection, Root, db_session=None),
        'item_deserializer': default_serializer_or_deserializer(deserialize_item, Root, db_session=None),
        'attr_to_use_in_url': 'name'
    },
    Level2: {
        'url_name': 'level2s',
        'item_serializer': default_serializer_or_deserializer(serialize_item, Root, db_session=None),
        'collection_serializer': default_serializer_or_deserializer(serialize_collection, Root, db_session=None),
        'item_deserializer': default_serializer_or_deserializer(deserialize_item, Root, db_session=None),
        'attr_to_use_in_url': 'name'
    },
    Level3: {
        'url_name': 'level3s',
        'item_serializer': default_serializer_or_deserializer(serialize_item, Root, db_session=None),
        'collection_serializer': default_serializer_or_deserializer(serialize_collection, Root, db_session=None),
        'item_deserializer': default_serializer_or_deserializer(deserialize_item, Root, db_session=None),
        'attr_to_use_in_url': 'name'
    },
}


def test_params_from_path():
    correct_params = level_3_params()
    p = params_from_path(g, path)
    assert p == correct_params


def test_url_for_path():
    collection_url, item_url = urls_for_path(path, config_name_provider(config))
    correct_collection_url = '/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s'
    correct_item_url = '/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s/<level_3_id>'
    assert collection_url == correct_collection_url
    assert item_url == correct_item_url


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
