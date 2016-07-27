import networkx as nx
from itertools import chain
from six.moves import zip, map, range
from functools import partial
from pytest import fixture
from rest.helpers import tails, add_item
from rest.handlers import serialize_item, create_schema
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
import json

ModelBase = declarative_base()


class EqualByName(object):
    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name


class DictRepr(object):
    def __repr__(self):
        as_dict = serialize_item(create_schema(self.__class__)(), self)
        as_dict['__class__'] = str(self.__class__)
        return json.dumps(as_dict)


class Root(ModelBase, EqualByName, DictRepr):
    __tablename__ = 'roots'
    name = Column(String, primary_key=True, nullable=False)
    level1s = relationship('Level1')


class Level1(ModelBase, EqualByName, DictRepr):
    __tablename__ = 'level1s'
    name = Column(String, primary_key=True, nullable=False)
    root_pk = Column(String, ForeignKey('roots.name'))
    level2s = relationship('Level2')


class Level2(ModelBase, EqualByName, DictRepr):
    __tablename__ = 'level2s'
    name = Column(String, primary_key=True, nullable=False)
    level1_pk = Column(String, ForeignKey('level1s.name'))
    level3s = relationship('Level3')


class Level3(ModelBase, EqualByName, DictRepr):
    __tablename__ = 'level3s'
    name = Column(String, primary_key=True, nullable=False)
    level2_pk = Column(String, ForeignKey('level2s.name'))


association_table = Table(
    'association',
    ModelBase.metadata,
    Column('parent_id', Integer, ForeignKey('parents.id')),
    Column('child_id', Integer, ForeignKey('children.id')),
)


class Parent(ModelBase, EqualByName, DictRepr):
    __tablename__ = 'parents'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    children = relationship(
        "Child",
        secondary=association_table,
        back_populates="parents",
        collection_class=set
    )


class Child(ModelBase, EqualByName, DictRepr):
    __tablename__ = 'children'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    parents = relationship(
        "Parent",
        secondary=association_table,
        back_populates="children",
        collection_class=set
    )
    grandchildren = relationship('Grandchild')


class Grandchild(ModelBase, EqualByName, DictRepr):
    __tablename__ = 'blabla'
    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey('children.id'))
    name = Column(String, nullable=False)


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


def hierarchy_full_data(session, count=2):
    items = make_items(hierarchy_graph(), Root, count=count)
    for i in items:
        session.add(i)
    return items


def circular_full_data(session, count=2):
    class PseudoRoot(object):
        def __init__(self, name):
            self.name = name
            self.parents = []
            self.children = []

    g = cyclic_graph()
    g.add_edge(PseudoRoot, Parent, rel_attr='parents')
    g.add_edge(PseudoRoot, Child, rel_attr='children')
    items = make_items(g, PseudoRoot, count=count)
    real_roots = chain.from_iterable(((i.parents + i.children) for i in items))
    for r in real_roots:
        session.add(r)
    return items


def make_items(graph, model_class, parent_name=(), count=2, join_char='_'):
    name_parts = parent_name + (model_class.__name__.lower(),)

    items = [model_class(
        name=join_char.join(chain(name_parts, (str(i),)))
    )
        for i in range(count)]

    one_to_many = [r for r in graph.successors_iter(model_class)
                   if (r, model_class) not in graph.edges()]

    rel_items = [(i, rel,  make_items(graph, rel, (i.name, ), count))
                 for i in items for rel in one_to_many]

    for i, rel, items_ in rel_items:
        rel_attr = graph[i.__class__][rel]['rel_attr']
        getattr(i, rel_attr).extend(items_)

    many_to_many = [(i1, from_rel, to_rel, (from_items, to_items))
                    for i1, from_rel, from_items in rel_items
                    for i2, to_rel, to_items in rel_items
                    if i1 == i2 and (from_rel, to_rel) in graph.edges()]

    def by_counter(rel_item):
        return rel_item.name.split(join_char)[-1]

    sorter = partial(sorted, key=by_counter)

    for item, from_rel, to_rel, iss in many_to_many:
        rel_attr = graph[from_rel][to_rel]['rel_attr']
        for from_item, to_item in zip(*map(sorter, iss)):
            add_item(from_item, rel_attr, to_item)

    return items


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
