from rest.introspect import pk_attr_name, related_models
from tests.fixtures import Root, Level1, Child, Parent


def test_pk_name_for_model():
    assert ('name', str) == pk_attr_name(Root)
    assert ('id', int) == pk_attr_name(Child)


def test_related_models():
    assert {Level1: 'level1s'} == related_models(Root)
    assert {Child: 'children'} == related_models(Parent)
    assert {Parent: 'parents'} == related_models(Child)
