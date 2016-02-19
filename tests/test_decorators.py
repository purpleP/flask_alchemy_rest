from pytest import fixture
from rest.helpers import merge


@fixture()
def initial_schema():
    return {
        'some key': {
            'properties': {
                'property': {
                    'type': 'string'
                }
            }
        }
    }


@fixture()
def metas():
    return {
        'some key': {
            'title': 'Some Resource',
            'properties': {
                'property': {
                    'title': 'Some Property'
                }
            }
        }
    }


@fixture()
def correct_schema(initial_schema, metas):
    correct_schema = dict(initial_schema)
    correct_schema['some key']['title'] = metas['some key']['title']
    title = metas['some key']['properties']['property']['title']
    correct_schema['some key']['properties']['property']['title'] = title
    return correct_schema


def test_merge(initial_schema, metas, correct_schema):
    assert correct_schema == merge(initial_schema, metas)
