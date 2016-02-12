from marshmallow.fields import String, Number, Integer, Boolean, Nested
from marshmallow.validate import Length, Range, OneOf


def to_jsonschema(mschema):
    return reduce(
        to_jsonschema_field,
        mschema.declared_fields.values(),
        {'type': 'object', 'properties': {}}
    )


def to_jsonschema_field(current_schema, field):
    name = field.name
    if field.required:
        current_schema['required'].append(name)
    property_dict = {}
    property_dict['type'] = type_mapping[field.__class__]
    property_dict.update(property_mapping[field.__class__](field))
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


def nested(field):
    return to_jsonschema(field.schema)


type_mapping = {
    String: 'string',
    Number: 'number',
    Integer: 'integer',
    Nested: 'object',
    Boolean: 'boolean',
}

property_mapping = {
    String: string,
    Number: number,
    Integer: number,
    Nested: nested,
    Boolean: boolean,
}
