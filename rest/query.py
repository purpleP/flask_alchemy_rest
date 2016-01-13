from collections import namedtuple
from functools import partial

QueryParams = namedtuple(
        'QueryParams',
        ['model', 'exposed_attr', 'exposed_attr_value', 'fk_attr', 'linked_attr'])


def filter_query(query, model, filter_attr, filter_value):
    return query.filter(getattr(model, filter_attr) == filter_value)


def fk_query(db_session, model, linked_attr, item_filter, fk_filter=None):
    item_filtered = item_filter(db_session.query(getattr(model, linked_attr)))
    if fk_filter:
        return fk_filter(item_filtered)
    else:
        return item_filtered


def create_queries(db_session, const_params, filter_values):
    model, exposed_attr, fk_attr, linked_attr = const_params[0]
    cq = db_session.query(model)
    iq = None
    fkq = None
    if len(filter_values) > 0:
        item_filter = partial(
            filter_query,
            model=model,
            filter_attr=exposed_attr,
            filter_value=filter_values[0]
        )
        fkq = partial(
                fk_query,
                db_session=db_session,
                model=model,
                item_filter=item_filter
        )
        if len(const_params) > 1:
            _cq, _iq, _fkq = create_queries(
                db_session,
                const_params[1:],
                filter_values[1:]
            )
            fk_filter = partial(
                filter_query,
                model=model,
                filter_attr=fk_attr,
                filter_value=_fkq(linked_attr=linked_attr)
            )
            cq = fk_filter(cq)
            fkq = partial(fkq, fk_filter=fk_filter)
        iq = item_filter(cq)
    return cq, iq, fkq
