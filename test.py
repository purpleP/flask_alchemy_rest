from functools import partial

from flask import Flask, jsonify
from marshmallow_sqlalchemy import ModelSchema
from rest.query import QueryParam, create_query
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.test_query import Level3, Root, Level1, Level2, ModelBase

app = Flask(__name__)

db_url = 'sqlite:///:memory:'
engine = create_engine(db_url, convert_unicode=True)
db_session = sessionmaker(autocommit=False,
                          autoflush=False,
                          bind=engine)()


def serialize_item(schema, item):
    return schema.dump(item).data


def serialize_collection(schema, collection):
    return schema.dump(collection, many=True).data


ModelBase.metadata.create_all(engine)

root = Root(name='root')
l1 = Level1(name='level1')
level2 = Level2(name='level2')
level3 = Level3(name='level3')
root.level1s.append(l1)
l1.level2s.append(level2)
level2.level3s.append(level3)
db_session.add(root)
db_session.commit()


class RootSchema(ModelSchema):
    class Meta:
        model = Root


class Level1Schema(ModelSchema):
    class Meta:
        model = Level1


class Level2Schema(ModelSchema):
    class Meta:
        model = Level2


class Level3Schema(ModelSchema):
    class Meta:
        model = Level3


def handle_request(query_params, schema, **kwargs):
    ordered_ids = reversed(sorted(kwargs.keys()))
    params = [p._replace(foreign_key_value=kwargs[_id]) for p, _id in zip(query_params, ordered_ids)]
    items = create_query(db_session, params).all()
    return jsonify({'items': serialize_collection(schema(), items)})


query_params = (
    QueryParam(
            model=Level3,
            attr_name=None,
            foreign_key_name='level2_pk',
            foreign_key_value=None
    ),
    QueryParam(
            model=Level2,
            attr_name='name',
            foreign_key_name='level1_pk',
            foreign_key_value=None
    ),
    QueryParam(
            model=Level1,
            attr_name='name',
            foreign_key_name='root_pk',
            foreign_key_value=None
    ),
)


schema_meta = type('Meta', (object,), {'model': Level3})
handler = partial(handle_request, query_params, type('Level3Schema', (ModelSchema,), {'Meta': schema_meta}))

app.add_url_rule('/roots/<level_0_id>/level1s/<level_1_id>/level2s/<level_2_id>/level3s', endpoint='1',
                 view_func=handler, methods=('GET',))
app.run()
