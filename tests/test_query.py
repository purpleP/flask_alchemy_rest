from rest.hierarchy_traverser import sublists
from rest.introspect import find

from rest.query import create_queries
from tests.fixtures import filter_values, params


def test_create_query(state):
    ses, models = state
    check_paths(models, params(), filter_values(), ses)


def check_paths(models, ps, fvs, ses):
    pss = [list(reversed(sl)) for sl in sublists(list(reversed(ps)))]
    fvss = [list(reversed(fvss)) for fvss in sublists(list(reversed(fvs)))]
    _check_paths(fvss, models, pss, ses)
    partial_filter_values = [[None] + fvss[1:] for fvss in fvss]
    _check_paths(partial_filter_values, models, pss, ses)


def _check_paths(fvss, models, pss, ses):
    [check_path(ses, ps, ms, fvs)
     for ms, ps, fvs in zip(reversed(models), pss, fvss)]


def check_path(session, ps, list, fvs):
    cq, iq, _ = create_queries(session, ps, fvs)
    assert list == cq.all()
    if fvs[0]:
        assert find(lambda i: i.name == fvs[0], list) == iq.one()

