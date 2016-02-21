from pytest import fixture, fail
from rest.generators import object_
from jsonschema import validate, ValidationError


@fixture()
def schema():
    return {
        'type': 'object',
        'properties': {
            'p1': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 100
            },
            'p2': {
                'type': 'number',
                'minimum': 0.1,
                'maximum': 0.9
            },
            'p3': {
                'type': 'boolean',
            },
            'p4': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 100
            },
            'p5': {
                'type': 'object',
                'properties': {
                    'p1': {
                        'type': 'string',
                        'minLength': 1,
                        'maxLength': 100
                    },
                },
                'required': ['p1']
            }
        },
        'required': ['p1', 'p2', 'p3', 'p4']
    }


def test_generator(schema):
    try:
        validate(object_(schema), schema)
    except ValidationError as e:
        fail(str(e))
