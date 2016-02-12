import pytest
from marshmallow import Schema
from marshmallow.fields import String, Number
from marshmallow.validate import Length
from rest.schema import to_jsonschema


class BasicTestSchema(Schema):
    basic_jsonschema = {
        'type': 'object',
        'properties': {}
    }

    @classmethod
    def add_properties(cls, schema):
        pass

    @classmethod
    def correct_jsonschema(cls):
        return cls.add_properties(cls.basic_jsonschema)


class UnlimitedStringSchema(BasicTestSchema):
    name = String()

    @classmethod
    def add_properties(cls, schema):
        schema['properties']['name'] = {
            'type': 'string'
        }
        return schema


class LimitedStringSchema(UnlimitedStringSchema):
    name = String(validate=Length(min=5, max=10))

    @classmethod
    def add_properties(cls, schema):
        parent_schema = super(LimitedStringSchema, cls).add_properties(schema)
        parent_schema['properties']['name']['minLength'] = 5
        parent_schema['properties']['name']['maxLength'] = 10
        return parent_schema


@pytest.mark.parametrize('schema', [
    UnlimitedStringSchema(),
    LimitedStringSchema(),
])
def test_schema_transformation(schema):
    jschema = to_jsonschema(schema)
    assert jschema == schema.correct_jsonschema()
