from pytest import fixture
from rest.hierarchy_traverser import sublists
from rest.introspect import find

from rest.query import create_query, QueryParam, foreign_key_query, subcollection_query, item_query, \
    top_level_collection_query, create_query
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


root_params = (
    QueryParam(
        model=Root,
        attr_name=None,
        foreign_key_name=None,
        foreign_key_value=None,
    ),
)

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
    return _session, ([level3], [level2], [l1], [root])


def test_create_q(state):
    ses, models = state
    params = (
        (Level3, 'name', 'level3', 'level2_pk', 'name'),
        (Level2, 'name', 'level2', 'level1_pk', 'name'),
        (Level1, 'name', 'level1', 'root_pk', 'name'),
        (Root, 'name', 'root', None, None),
    )
    pss = [list(reversed(sl)) for sl in sublists(list(reversed(params)))]
    [check(ses, ps, ms) for ms, ps in zip(reversed(models), pss)]


def check(session, params, list):
    cq, iq, _ = create_query(session, params)
    _, _, filter_value, _, _ = params[0]
    assert list == cq.all()
    assert find(lambda i: i.name == filter_value, list) == iq.one()



