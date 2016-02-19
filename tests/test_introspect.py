from rest.introspect import pk_attr_name, related_models
from sqlalchemy.orm.base import ONETOMANY, MANYTOMANY
from sqlalchemy.util import symbol
from tests.fixtures import Root, Level1, Child, Parent, Grandchild


def test_pk_name_for_model():
    assert ('name', str) == pk_attr_name(Root)
    assert ('id', int) == pk_attr_name(Child)


def test_related_models():
    assert {Level1: ('level1s', ONETOMANY)} == related_models(Root)
    assert {Child: ('children', MANYTOMANY)} == related_models(Parent)
    assert {Parent: ('parents', MANYTOMANY), Grandchild: ('grandchildren', ONETOMANY)} == related_models(Child)
