from functools import partial
import pytest

from rest.query import query
from tests.fixtures import (
    hierarchy_full_data,
    circular_full_data,
    session,
    Root,
    Level1,
    Level2,
    Level3,
    Child,
    Parent,
)


class Helper(object):

    def __init__(self, session, data_creator):
        self.session = session
        self.roots = data_creator(session)
        self.session.commit()


@pytest.mark.parametrize('helper,query,correct_result', [
    (
        Helper(session(), hierarchy_full_data),
        partial(
            query,
            model_to_query=Level3,
            join_attrs=(Level2, Level1, Root),
            attrs_to_filter=(Level2.name, Level1.name, Root.name),
            keys=(
                'root_0_level1_0_level2_0',
                'root_0_level1_0',
                'root_0',
            )
        ),
        lambda roots: [
            l3
            for r in roots if r.name == 'root_0'
            for l1 in r.level1s if l1.name == 'root_0_level1_0'
            for l2 in l1.level2s if l2.name == 'root_0_level1_0_level2_0'
            for l3 in l2.level3s
        ]
    ),
    (
        Helper(session(), hierarchy_full_data),
        partial(
            query,
            model_to_query=Level3,
            join_attrs=(Level2, Level1, Root),
            attrs_to_filter=(Level3.name, Level2.name, Level1.name, Root.name),
            keys=(
                'root_0_level1_0_level2_0_level3_0',
                'root_0_level1_0_level2_0',
                'root_0_level1_0',
                'root_0',
            )
        ),
        lambda roots: [
            l3
            for r in roots if r.name == 'root_0'
            for l1 in r.level1s if l1.name == 'root_0_level1_0'
            for l2 in l1.level2s if l2.name == 'root_0_level1_0_level2_0'
            for l3 in l2.level3s
            if l3.name == 'root_0_level1_0_level2_0_level3_0'
        ]
    ),
    (
        Helper(session(), circular_full_data),
        partial(
            query,
            model_to_query=Child,
            join_attrs=(Parent.children,),
            attrs_to_filter=(Parent.name,),
            keys=(
                'pseudoroot_0_parent_0',
                'pseudoroot_0',
            )
        ),
        lambda roots: [
            child
            for r in roots if r.name == 'pseudoroot_0'
            for p in r.parents if p.name == 'pseudoroot_0_parent_0'
            for child in p.children
        ]
    ),
])
def test_query(helper, query, correct_result):
    result = query(session=helper.session).all()
    assert result == correct_result(helper.roots)
