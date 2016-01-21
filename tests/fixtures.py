import networkx as nx
from pytest import fixture
from rest.hierarchy_traverser import tails

from sqlalchemy import Column, String, ForeignKey, create_engine, Integer, \
     Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

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


association_table = Table(
    'association',
    ModelBase.metadata,
    Column('parent_id', Integer, ForeignKey('parents.id')),
    Column('child_id', Integer, ForeignKey('children.id'))
)


class Parent(ModelBase):
    __tablename__ = 'parents'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    children = relationship(
            "Child",
            secondary=association_table,
            back_populates="parents")


class Child(ModelBase):
    __tablename__ = 'children'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    parents = relationship(
            "Parent",
            secondary=association_table,
            back_populates="children")


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


@fixture(scope='module')
def session():
    engine = create_engine(
            'sqlite:///:memory:',
            echo=False,
            convert_unicode=True
    )
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    ModelBase.metadata.create_all(engine)
    return session


@fixture(scope='module')
def state():
    _session = session()
    root = Root(name='root')
    l1 = Level1(name='level1')
    level2, level3 = items()
    l1.level2s.append(level2)
    root.level1s.append(l1)
    _session.add(root)
    _session.commit()
    return _session, ([level3], [level2], [l1], [root])


def hierarchy_data():
    root = Root(name='root')
    l1 = Level1(name='level1')
    l2 = Level2(name=u'level2')
    l3 = Level3(name=u'level3')
    return [root], [l1], [l2], [l3]


def cycled_data():
    adam = Parent(name='Adam')
    eve = Parent(name='Eve')
    cain = Child(name='Cain')
    abel = Child(name='Abel')
    return adam, eve, cain, abel


level3_item_url = '/roots/root/level1s/level1/level2s/level2/level3s/level3'
level3_collection_url = '/roots/root/level1s/level1/level2s/level2/level3s'
level3_item_rule = '/roots/<level_0_id>/level1s/<level_1_id>/level2s/' \
                   '<level_2_id>/level3s/<level_3_id>'
level3_collection_rule = '/roots/<level_0_id>/level1s/<level_1_id>/level2s/' \
                         '<level_2_id>/level3s'
config = {
    Root: {
        'exposed_attr': 'name',
    },
    Level1: {
        'exposed_attr': 'name',
    },
    Level2: {
        'exposed_attr': 'name',
    },
    Level3: {
        'exposed_attr': 'name',
    },
}
full_path = (Level3, Level2, Level1, Root)


def paths():
    pairs = [(m, config[m]['exposed_attr']) for m in full_path]
    return list(reversed(tails(pairs)))[1:]


@fixture(scope='module')
def models_graphs():
    hierarchy = nx.DiGraph()
    hierarchy.add_edge(Root, Level1, rel_attr='level1s')
    hierarchy.add_edge(Level1, Level2, rel_attr='level2s')
    hierarchy.add_edge(Level2, Level3, rel_attr='level3s')
    cyclic = nx.DiGraph()
    cyclic.add_edge(Parent, Child, rel_attr='children')
    cyclic.add_edge(Child, Parent, rel_attr='parents')
    return hierarchy, cyclic
