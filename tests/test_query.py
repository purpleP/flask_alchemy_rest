from functools import partial

from rest.hierarchy_traverser import tails
from rest.query import query
from tests.fixtures import paths, state


def test_query(state):
    session, data = state
    keys = list(reversed(tails([d[0].name for d in data[1:]])))
    for subp, av, d in zip(paths(), keys[:-1], reversed(data)):
        check_column_query(session, subp, av, d)

    for subp, av, d in zip(paths(), keys, reversed(data)):
        check_item_query(session, subp, av, d)


def check_item_query(session, path, keys, correct_items):
    iq = partial(query, session, path)
    result = iq(keys).all()
    assert result == correct_items


def check_column_query(session, path, keys, correct_items):
    cq = partial(query, session, path)
    result = cq(keys).all()
    assert result == correct_items
