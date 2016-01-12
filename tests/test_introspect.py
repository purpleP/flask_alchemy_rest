from rest.introspect import pk_attr_name
from tests.test_query import Root


def test_pk_name_for_model():
    assert 'name' == pk_attr_name(Root)
