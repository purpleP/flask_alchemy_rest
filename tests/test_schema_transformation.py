import pytest
from marshmallow import Schema
from marshmallow.fields import String, Number, Nested
from marshmallow.validate import Length, Range
from rest.schema import to_jsonschema


class BasicTestParam(object):
    def __init__(self):
        self.basic_jsonschema = {
            'type': 'object',
            'properties': {}
        }

    def add_properties(self, schema):
        return schema

    @property
    def correct_jsonschema(self):
        return self.add_properties(self.basic_jsonschema)


class StringSchema(Schema):
    name = String()


class StringParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['name'] = {
            'type': 'string'
        }
        return schema


class LimitedStringSchema(Schema):
    name = String(validate=Length(min=5, max=10))


class LimitedStringParam(StringParam):
    def add_properties(self, schema):
        parent_schema = super(LimitedStringParam, self).add_properties(schema)
        parent_schema['properties']['name']['minLength'] = 5
        parent_schema['properties']['name']['maxLength'] = 10
        return parent_schema


class NumberSchema(Schema):
    order = Number()


class NumberParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['order'] = {
            'type': 'number'
        }
        return schema


class LimitedNumberSchema(Schema):
    order = Number(validate=Range(min=5, max=10))


class LimitedNumberParam(NumberParam):
    def add_properties(self, schema):
        parent_schema = super(LimitedNumberParam, self).add_properties(schema)
        parent_schema['properties']['order']['minimum'] = 5
        parent_schema['properties']['order']['maximum'] = 10
        return parent_schema


class NestedSchema(Schema):
    order_info = Nested(StringSchema)


class NestedParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['order_info'] = {
            'type': 'object'
        }
        schema['properties']['order_info'].update(
            StringParam().correct_jsonschema
        )
        return schema


@pytest.mark.parametrize('mschema,param', [
    (StringSchema(), StringParam()),
    (LimitedStringSchema(), LimitedStringParam()),
    (NumberSchema(), NumberParam()),
    (LimitedNumberSchema(), LimitedNumberParam()),
    (NestedSchema(), NestedParam()),
])
def test_schema_transformation(mschema, param):
    jschema = to_jsonschema(mschema)
    assert jschema == param.correct_jsonschema
