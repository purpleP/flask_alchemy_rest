from marshmallow.fields import String, Number
from marshmallow.validate import Length, Range


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
    transformer = transformers[field.__class__]
    data = {name: transformer(field)}
    current_schema['properties'].update(data)
    return current_schema


def string(field):
    assert isinstance(field, String)
    data = {'type': 'string'}
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
    return data


def number(field):
    assert isinstance(field, Number)
    data = [('type', 'number')]
    for v in field.validators:
        if isinstance(v, Range):
            if v.min:
                data['minimum'] = v.min
            if v.max:
                data['maximum'] = v.max
    return data


transformers = {
    String: string,
    Number: number,
}
