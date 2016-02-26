from pytest import fixture
from rest.helpers import merge


@fixture()
def initial_schema():
    return {
        'some key': {
            'properties': {
                'p1': {
                    'type': 'string'
                }
            },
            'required': ['p1']
        }
    }


@fixture()
def metas():
    return {
        'some key': {
            'title': 'Some Resource',
            'properties': {
                'p1': {
                    'title': 'Some Property'
                },
                'p2': {
                    'type': 'number'
                }
            },
            'required': ['p1', 'p2']
        }
    }


@fixture()
def correct_schema(initial_schema, metas):
    correct_schema = dict(initial_schema)
    correct_schema['some key']['title'] = metas['some key']['title']
    properties = correct_schema['some key']['properties']
    title = metas['some key']['properties']['p1']['title']
    properties['p1']['title'] = title
    properties['p2'] = metas['some key']['properties']['p2']
    required_initial = initial_schema['some key']['required']
    required_metas = metas['some key']['required']
    correct_schema['some key']['required'] = list(
        set(required_initial + required_metas)
    )
    return correct_schema


def test_merge(initial_schema, metas, correct_schema):
    assert correct_schema == merge(initial_schema, metas)
