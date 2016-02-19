import pytest
from marshmallow import Schema
from marshmallow.fields import (
    Boolean,
    Date,
    DateTime,
    Email,
    Integer,
    List,
    LocalDateTime,
    Nested,
    Number,
    String,
    Time,
)
from marshmallow.validate import Length, Range, Regexp
from rest.schema import to_jsonschema


class BasicTestParam(object):
    def __init__(self):
        self.basic_jsonschema = {
            'type': 'object',
            'properties': {},
            'required': []
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


class RegexpStringSchema(Schema):
    name = String(validate=Regexp('.'))


class RegexpStringParam(StringParam):
    def add_properties(self, schema):
        parent_schema = super(RegexpStringParam, self).add_properties(schema)
        parent_schema['properties']['name']['pattern'] = '.'
        return parent_schema


class StringEnumSchema(Schema):
    name = String(choices=('one', 'two'))


class StringEnumParam(String):
    def add_properties(self, schema):
        parent_schema = super(LimitedStringParam, self).add_properties(schema)
        parent_schema['properties']['name']['enum'] = ('one', 'two')
        return parent_schema


class NumberSchema(Schema):
    order = Number()


class NumberParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['order'] = {
            'type': 'number'
        }
        return schema


class IntegerSchema(Schema):
    order = Integer()


class IntegerParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['order'] = {
            'type': 'integer'
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


class LimitedIntegerSchema(Schema):
    order = Integer(validate=Range(min=5, max=10))


class LimitedIntegerParam(IntegerParam):
    def add_properties(self, schema):
        parent_schema = super(LimitedIntegerParam, self).add_properties(schema)
        parent_schema['properties']['order']['minimum'] = 5
        parent_schema['properties']['order']['maximum'] = 10
        return parent_schema


class BooleanSchema(Schema):
    is_important = Boolean()


class BooleanParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['is_important'] = {
            'type': 'boolean'
        }
        return schema


class ListSchema(Schema):
    items = List(Boolean)


class ListParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['items'] = {
            'type': 'array',
            'items': {
                'type': 'boolean'
            }
        }
        return schema


class DateTimeSchema(Schema):
    a_long_time_ago = DateTime()


class DateTimeParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['a_long_time_ago'] = {
            'type': 'string',
            'format': 'date-time'
        }
        return schema


class LocalDateTimeSchema(Schema):
    a_long_time_ago = LocalDateTime()


class LocalDateTimeParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['a_long_time_ago'] = {
            'type': 'string',
            'format': 'date-time'
        }
        return schema


class DateSchema(Schema):
    a_long_time_ago = Date()


class DateParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['a_long_time_ago'] = {
            'type': 'string',
            'format': 'date-time'
        }
        return schema


class TimeSchema(Schema):
    a_long_time_ago = Time()


class TimeParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['a_long_time_ago'] = {
            'type': 'string',
            'format': 'date-time'
        }
        return schema


class EmailSchema(Schema):
    email_address = Email()


class EmailParam(BasicTestParam):
    def add_properties(self, schema):
        schema['properties']['email_address'] = {
            'type': 'string',
            'format': 'email'
        }
        return schema


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
    (StringEnumSchema(), StringParam()),
    (NumberSchema(), NumberParam()),
    (LimitedNumberSchema(), LimitedNumberParam()),
    (IntegerSchema(), IntegerParam()),
    (LimitedIntegerSchema(), LimitedIntegerParam()),
    (BooleanSchema(), BooleanParam()),
    (NestedSchema(), NestedParam()),
    (ListSchema(), ListParam()),
    (DateTimeSchema(), DateTimeParam()),
    (LocalDateTimeSchema(), LocalDateTimeParam()),
    (DateSchema(), DateParam()),
    (TimeSchema(), TimeParam()),
    (EmailSchema(), EmailParam()),
    (RegexpStringSchema(), RegexpStringParam()),
])
def test_schema_transformation(mschema, param):
    jschema = to_jsonschema(mschema)
    assert jschema == param.correct_jsonschema
