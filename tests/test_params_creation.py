from rest.hierarchy_traverser import RelationshipInfo
from rest.query import QueryParam, params_from_path, url_for_path
from tests.test_query import Level3, Level2, Level1, Root
import networkx as nx

g = nx.DiGraph()
g.add_edge(Root, Level1, rel=RelationshipInfo('name', 'root_pk'))
g.add_edge(Level1, Level2, rel=RelationshipInfo('name', 'level1_pk'))
g.add_edge(Level2, Level3, rel=RelationshipInfo('name', 'level2_pk'))
path = [Level3, Level2, Level1, Root]


def test_params_from_path():
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
        ),
    )
    params = params_from_path(g, path)
    assert params == correct_params


def test_url_for_path():
    collection_url, item_url = url_for_path(g, path)
    correct_collection_url = '/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s'
    correct_item_url = '/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s/<level_3_id>'
    assert collection_url == correct_collection_url
    assert item_url == correct_item_url
