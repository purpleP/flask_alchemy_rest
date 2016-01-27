from functools import partial

from rest.helpers import tails
from rest.query import query, join, filter_, join_and_filter
from tests.fixtures import paths, state, Parent, Child, session, Root, \
    full_path, query_modifiers
from tests.test_handlers import parent_with_child, parent_child


def test_query(state):
    session, data = state
    keys = list(reversed(tails([d[0].name for d in data[1:]])))
    for values, d, model_to_query in zip(keys[:-1], reversed(data),
                                         reversed(full_path)):
        check_column_query(session, model_to_query,
                           query_modifiers()[model_to_query], values, d)

    for value, d, model_to_query in zip(keys, reversed(data),
                                        reversed(full_path)):
        check_item_query(session, model_to_query,
                         query_modifiers()[model_to_query], value, d)


def check_item_query(session, model_to_query, query_modifiers, keys,
                     correct_items):
    iq = partial(query, session, model_to_query, query_modifiers)
    result = iq(keys).all()
    assert result == correct_items


def check_column_query(session, model_to_query, query_modifiers, keys,
                       correct_items):
    cq = partial(query, session, model_to_query, query_modifiers)
    result = cq(keys).all()
    assert result == correct_items


def test_many_to_many_query(session):
    parent_with_child(session)
    session.commit()
    keys = (1,)
    jf = partial(
            join_and_filter,
            left_join=Parent,
            right_join=Child.parents,
            left=Parent.id
    )
    query_modifiers = (jf, )
    children = query(session, model_to_query=Child, query_modifiers=query_modifiers, keys=keys).all()
    assert len(children) == 0
