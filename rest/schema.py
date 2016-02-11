from marshmallow.fields import String, Number
from marshmallow.validate import Length, Range


def to_json_schema_field(name, field, current_schema={}):
    if field.required:
        current_schema['required'].append(name)
    transformer = transformers[field.__class__]
    data = transformer(name, field, current_schema)
    current_schema['properties'][name] = dict(data)
    return current_schema


def string(name, field, current_schema={}):
    assert isinstance(field, String)
    data = [('type', 'string')]
    for v in field.validators:
        if isinstance(v, Length):
            if v.min:
                data.append('minLength', v.min)
            if v.max:
                data.append('maxLength', v.max)
            if v.equal:
                data.append('minLength', v.equal)
                data.append('maxLength', v.equal)
    return data


def number(name, field, currect_schema):
    assert isinstance(field, Number)
    data = [('type', 'number')]
    for v in field.validators:
        if isinstance(v, Range):
            if v.min:
                data.append('minimum', v.min)
            if v.max:
                data.append('maximum', v.max)
    return data


transformers = {
    String: string,
    Number: number,
}
        
