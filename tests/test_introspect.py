from rest.introspect import pk_attr_name, fk_attr_for
from tests.fixtures import Root, Level1


def test_pk_name_for_model():
    assert 'name' == pk_attr_name(Root)


def test_fk_attr_for():
    assert 'name' == fk_attr_for(Level1, Root)
