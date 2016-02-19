from inspect import getmro

from helpers import find
from marshmallow.fields import (
    Boolean,
    DateTime,
    LocalDateTime,
    Time,
    Date,
    Integer,
    List,
    Nested,
    Number,
    String,
    Email,
)
from marshmallow.validate import Length, OneOf, Range, Regexp


def to_jsonschema(mschema):
    return reduce(
        to_jsonschema_field,
        mschema._declared_fields.items(),
        {'type': 'object', 'properties': {}, 'required': []}
    )


def to_jsonschema_field(current_schema, name_and_field):
    attr_name, field = name_and_field
    if field.__class__ in type_mapping:
        if field.name:
            name = field.name
        else:
            name = attr_name
        if field.required:
            current_schema['required'].append(name)
        property_dict = {'type': type_mapping[field.__class__]}
        most_specific_mapped_class = find(
            lambda c: c in property_mapping.keys(),
            getmro(field.__class__)
        )
        if most_specific_mapped_class:
            property_dict.update(
                property_mapping[most_specific_mapped_class](field)
            )
            current_schema['properties'].update({name: property_dict})
    return current_schema


def string(field):
    data = {}
    for v in field.validators:
        if isinstance(v, Length):
            if v.min:
                data['minLength'] = v.min
            if v.max:
                data['maxLength'] = v.max
            if hasattr(v, 'equal'):
                if v.equal:
                    data['minLength'] = v.equal
                    data['maxLength'] = v.equal
        if isinstance(v, OneOf):
            data['enum'] = v.choices
        if isinstance(v, Regexp):
            data['pattern'] = v.regex.pattern

    return data


def number(field):
    property_dict = {}
    for v in field.validators:
        if isinstance(v, Range):
            if v.min:
                property_dict['minimum'] = v.min
            if v.max:
                property_dict['maximum'] = v.max
    return property_dict


def boolean(field):
    return {}


def list_(field):
    if field.container.__class__ in type_mapping:
        return {
            'items': {
                'type': type_mapping[field.container.__class__]
            }
        }
    else:
        return {}


def datetime_(field):
    return {'format': 'date-time'}


def email(field):
    return {'format': 'email'}


def nested(field):
    return to_jsonschema(field.schema)


type_mapping = {
    String: 'string',
    Number: 'number',
    Integer: 'integer',
    List: 'array',
    DateTime: 'string',
    LocalDateTime: 'string',
    Time: 'string',
    Date: 'string',
    Nested: 'object',
    Boolean: 'boolean',
    Email: 'string',
}

property_mapping = {
    String: string,
    Number: number,
    Integer: number,
    List: list_,
    DateTime: datetime_,
    LocalDateTime: datetime_,
    Time: datetime_,
    Date: datetime_,
    Nested: nested,
    Boolean: boolean,
    Email: email,
}
