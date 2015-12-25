from unittest import TestCase

from rest.query import create_query, QueryParam
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
    __tablename__ = 'levels3'
    name = Column(String, primary_key=True)
    level2_pk = Column(String, ForeignKey('level2s.name'))

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        if not isinstance(other, Level3):
            return False
        return self.name == other.name and self.level2_pk == other.level2_pk


class TestQuery(TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:', echo=True, convert_unicode=True)
        self.session = sessionmaker(autocommit=False,
                                    autoflush=False,
                                    bind=self.engine)()
        ModelBase.metadata.create_all(self.engine)

        root = Root(name='root')
        l1 = Level1(name='level1')
        self.level2 = Level2(name='level2')
        l1.level2s.append(self.level2)
        root.level1s.append(l1)
        self.level3 = Level3(name='level3')
        self.level2.level3s.append(self.level3)
        self.session.add(root)
        self.session.commit()

    def test_query(self):
        params = (
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
        level2 = create_query(self.session, params).one()
        self.assertEquals(level2, self.level2)
        params = (
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
        level3 = create_query(self.session, params).one()
        self.assertEquals(level3, self.level3)
