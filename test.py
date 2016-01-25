from functools import partial

from flask import Flask, session
from rest.endpoints import create_api
from rest.handlers import schema_maker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from tests.fixtures import Root, Parent, Child, ModelBase


app = Flask('app')
@app.teardown_request
def remove_session(ex=None):
    db_session.remove()


def item_ser(authorized_schema, non_authorized_schema, item):
    user = session['user']
    if user == 'foo':
        return authorized_schema.dumps(item).data
    else:
        return non_authorized_schema.dumps(item).data


AuthorizedSchema = schema_maker(Parent)
NonAuthorizedSchema = schema_maker(Parent, meta_dict={'exclude': ('children',)})


def config_wrapper(config):
    config[Parent]['item_serializer'] = partial(item_ser, AuthorizedSchema(), NonAuthorizedSchema)
    return config


if __name__ == '__main__':
    app.debug = True
    engine = create_engine(
            'sqlite:///delme.db',
            echo=False,
            convert_unicode=True
    )
    db_session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )
    ModelBase.metadata.create_all(engine)
    create_api(Parent, db_session, app, config_decorator=config_wrapper)
    create_api(Child, db_session, app)



    app.run()
