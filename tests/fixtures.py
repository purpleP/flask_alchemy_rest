from functools import partial

import networkx as nx
from pytest import fixture
from rest.helpers import tails
from rest.query import filter_, join
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm.base import MANYTOMANY, ONETOMANY
from sqlalchemy.pool import StaticPool


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
    grandchildren = relationship('Grandchild')


class Grandchild(ModelBase):
    __tablename__ = 'blabla'
    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey('children.id'))
    name = Column(String)


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


@fixture()
def session():
    engine = create_engine(
            'sqlite://',
            echo=False,
            convert_unicode=True,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
    )
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    ModelBase.metadata.create_all(engine)
    return session


@fixture()
def h_data():
    root = Root(name='root')
    l1 = Level1(name='level1')
    l2 = Level2(name='level2')
    l3 = Level3(name='level3')
    return root, l1, l2, l3


@fixture()
def state(h_data, session):
    session.add(h_data[0])
    h_data[0].level1s.append(h_data[1])
    h_data[1].level2s.append(h_data[2])
    h_data[2].level3s.append(h_data[3])
    session.commit()
    return session, list(reversed(hierarchy_data(h_data)))


@fixture()
def hierarchy_data(h_data):
    return [[x] for x in h_data]


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


@fixture()
def query_modifiers():
    qms = tuple((partial(filter_, getattr(m, config[m]['exposed_attr'])),)
                for m in full_path)
    return {m: qms_ for m, qms_ in zip(full_path, tails(qms))}


@fixture()
def hierarchy_graph():
    g = nx.DiGraph()
    g.add_edge(Root, Level1, rel_attr='level1s', rel_type=ONETOMANY)
    g.add_edge(Level1, Level2, rel_attr='level2s', rel_type=ONETOMANY)
    g.add_edge(Level2, Level3, rel_attr='level3s', rel_type=ONETOMANY)
    return g


@fixture()
def cyclic_graph():
    g = nx.DiGraph()
    g.add_edge(Parent, Child, rel_attr='children', rel_type=MANYTOMANY)
    g.add_edge(Child, Parent, rel_attr='parents', rel_type=MANYTOMANY)
    g.add_edge(Child, Grandchild, rel_attr='grandchildren', rel_type=ONETOMANY)
    return g


@fixture
def data():
    root = Root(name='root1')
    l1 = Level1(name='level1_1')
    l2 = Level2(name='level2_1')
    l3 = Level3(name='level3_1')
    return root, l1, l2, l3


def l0_empty(s):
    pass


def l3_empty(s):
    root, l1, l2, l3 = data()
    l2_2 = Level2(name='level2_2')
    l1.level2s.append(l2)
    l1.level2s.append(l2_2)
    root.level1s.append(l1)
    s.add(root)
    return s


def hundred_roots_elements(s):
    root, l1, l2, l3 = data()
    l1.level2s.append(l2)
    root.level1s.append(l1)
    s.add(root)
    l3s = [Level3(name='foo' + str(i)) for i in range(100)]
    l2.level3s.extend(l3s)
    return s


def l3_non_empty(s):
    root, l1, l2, l3 = data()
    l1.level2s.append(l2)
    root.level1s.append(l1)
    l2.level3s.append(l3)
    s.add(root)
    return s


def parent_child(s):
    s.add(Parent(name='Eve'))
    s.add(Parent(name='Adam'))
    s.add(Child(name='Cain'))
    return s


def parent_with_child(s):
    eve = Parent(name='eve')
    adam = Parent(name='Adam')
    s.add(eve)
    s.add(adam)
    cain = Child(name='Cain')
    s.add(cain)
    adam.children.append(cain)
    return s


def search_session(s):
    root, l1, l2, l3 = data()
    l1.level2s.append(l2)
    root.level1s.append(l1)
    l2.level3s.append(l3)
    l2.level3s.append(Level3(name='find_me'))
    s.add(root)
    return s


child_collection_query_modifiers = (
    (
        (),
        partial(join, Parent, Child.parents),
    ),
    (
        partial(filter_, Parent.id),
    ),
)
