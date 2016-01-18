from rest.introspect import pk_attr_name, relation_info, related_models
from tests.fixtures import Root, Level1, Child, Parent


def test_pk_name_for_model():
    assert 'name' == pk_attr_name(Root)


def test_fk_attr_for():
    assert 'root_pk', 'name' == relation_info(Level1, Root)


def test_related_models():
    assert [Level1] == related_models(Root)
    assert [Child] == related_models(Parent)
    assert [Parent] == related_models(Child)
