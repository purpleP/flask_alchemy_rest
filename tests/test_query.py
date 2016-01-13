from pytest import fixture
from rest.hierarchy_traverser import sublists
from rest.introspect import find

from rest.query import create_queries
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


def items():
    level2 = Level2(name=u'level2')
    level3 = Level3(name=u'level3')
    level2.level3s.append(level3)
    return level2, level3


@fixture
def state():
    engine = create_engine(
        'sqlite:///:memory:',
        echo=False,
        convert_unicode=True
    )
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


def test_create_query(state):
    ses, models = state
    params = (
        (Level3, 'name', 'level2_pk', 'name'),
        (Level2, 'name', 'level1_pk', 'name'),
        (Level1, 'name', 'root_pk', 'name'),
        (Root, 'name', None, None),
    )
    filter_values = ['level3', 'level2', 'level1', 'root']
    pss = [list(reversed(sl)) for sl in sublists(list(reversed(params)))]
    fvss = [list(reversed(fvs)) for fvs in sublists(list(reversed(filter_values)))]
    [check(ses, ps, ms, fvs)
     for ms, ps, fvs in zip(reversed(models), pss, fvss)]
    fvss[-1] = fvss[-2]
    [check(ses, ps, ms, fvs)
     for ms, ps, fvs in zip(reversed(models), pss, fvss)]


def check(session, params, list, filter_values):
    cq, iq, _ = create_queries(session, params, filter_values)
    assert list == cq.all()
    if len(filter_values) > 0:
        assert find(lambda i: i.name == filter_values[0], list) == iq.one()

