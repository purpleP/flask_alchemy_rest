from pytest import fixture

from rest.query import create_query, QueryParam, foreign_key_query, subcollection_query, item_query
from sqlalchemy import create_engine, String, Column, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

ModelBase = declarative_base()


class Root(ModelBase):
    __tablename__ = 'roots'
    name = Column(String, primary_key=True)
    level1s = relationship('Level1')


class Level1(ModelBase):
    __tablename__ = 'level1s'
    name = Column(String, primary_key=True)
    root_pk = Column(String, ForeignKey('roots.name'))
    level2s = relationship('Level2')


class Level2(ModelBase):
    __tablename__ = 'level2s'
    name = Column(String, primary_key=True)
    level1_pk = Column(String, ForeignKey('level1s.name'))
    level3s = relationship('Level3')

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        if not isinstance(other, Level2):
            return False
        return self.name == other.name and self.level1_pk == other.level1_pk


class Level3(ModelBase):
    __tablename__ = 'level3s'
    name = Column(String, primary_key=True)
    level2_pk = Column(String, ForeignKey('level2s.name'))

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        if not isinstance(other, Level3):
            return False
        return self.name == other.name and self.level2_pk == other.level2_pk


level3_params = (
    QueryParam(
            model=Level3,
            attr_name=None,
            foreign_key_name='level2_pk',
            foreign_key_value='level2',
    ),
    QueryParam(
            model=Level2,
            attr_name='name',
            foreign_key_name='level1_pk',
            foreign_key_value='level1',
    ),
    QueryParam(
            model=Level1,
            attr_name='name',
            foreign_key_name='root_pk',
            foreign_key_value='root',
    ),
)

level2_params = (
    QueryParam(
            model=Level2,
            attr_name=None,
            foreign_key_name='level1_pk',
            foreign_key_value='level1',
    ),
    QueryParam(
            model=Level1,
            attr_name='name',
            foreign_key_name='root_pk',
            foreign_key_value='root',
    ),
)


def items():
    level2 = Level2(name=u'level2')
    level3 = Level3(name=u'level3')
    level2.level3s.append(level3)
    return level2, level3


@fixture
def state():
    engine = create_engine('sqlite:///:memory:', echo=False, convert_unicode=True)
    _session = sessionmaker(autocommit=False,
                            autoflush=False,
                            bind=engine)()
    ModelBase.metadata.create_all(engine)

    root = Root(name='root')
    l1 = Level1(name='level1')
    level2, level3 = items()
    l1.level2s.append(level2)
    root.level1s.append(l1)
    _session.add(root)
    _session.commit()
    return _session, level2, level3


def test_query(state):
    level2 = create_query(state[0], level2_params).one()
    assert level2 == state[1]
    level3 = create_query(state[0], level3_params).one()
    assert level3 == state[2]


def test_query_foreign_key(state):
    fk = foreign_key_query(state[0], level3_params[2:]).one()
    assert fk == (u'level1',)
    fk = foreign_key_query(state[0], level3_params[1:]).one()
    assert fk == (u'level2',)


def test_query_subcollection(state):
    queried_items = subcollection_query(state[0], level3_params).all()
    assert state[2] in queried_items
    assert len(queried_items) == 1

def test_query_item(state):
    item = item_query(state[0], level3_params, 'name', 'level3').one()
    assert state[2] == item
