from functools import partial

from rest.helpers import tails
from rest.query import query, zip_
from tests.fixtures import Child, full_path, query_modifiers, \
    parent_with_child, child_collection_query_modifiers


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


def add(x, y):
    return x + y


add2 = partial(add, 2)
add23 = partial(add2, 3)


def test_zip_():
    fss = ((add2, add23), (add2,))
    values = (1, 2)
    output = [f(*vs) for f, vs in zip_(fss, values)]
    assert output == [3, 5, 4]
    fss = ((add2, add23), (add2,), (add2,))
    output = [f(*vs) for f, vs in zip_(fss, values)]
    assert output == [5, 3, 4]


def test_many_to_many_query(session):
    parent_with_child(session)
    session.commit()
    keys = (1,)
    children_q = query(
            session,
            model_to_query=Child,
            query_modifiers=child_collection_query_modifiers,
            keys=keys
    )
    assert len(children_q.all()) == 0
