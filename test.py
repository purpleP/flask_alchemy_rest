from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.test_query import Level3, Root, Level1, Level2
from tests.fixtures import ModelBase, Root, Level1, Level2, Level3

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

app.run()
