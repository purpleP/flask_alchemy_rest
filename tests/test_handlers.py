import json
from collections import namedtuple
from functools import partial

import pytest
from flask import Flask
from rest.handlers import (
    create_handler,
    create_schema,
    data_handler,
    delete_item,
    delete_many_to_many,
    deserialize_item,
    get_collection,
    get_handler,
    get_item,
    non_root_adder,
    patch_item,
    post_item,
    post_item_many_to_many,
    root_adder,
    serialize_collection,
    serialize_item,
)
from rest.query import filter_, query
from tests.fixtures import (
    Child,
    Level2,
    Level3,
    Parent,
    Root,
    child_collection_query_modifiers,
    l0_empty,
    l3_empty,
    hundred_roots_elements,
    l3_non_empty,
    level3_collection_rule,
    level3_item_rule,
    parent_child,
    parent_with_child,
    query_modifiers,
    search_session,
    session,
)
from tests.flask_test_helpers import patch, post_json


def by_name_spec(name, query):
    return query.filter_by(name=name)


def client(handler_maker, methods, rule, s, *args, **kwargs):
    sess_modifier = kwargs.pop('session_modifier')
    sess_modifier(s)
    s.commit()
    app = Flask('foo')
    app.debug = True
    app.add_url_rule(
            rule=rule,
            endpoint='1',
            view_func=handler_maker(s, *args, **kwargs),
            methods=methods
    )
    return app.test_client()


def search_dict(name):
    spec_dict = {'name': 'by_name', 'args': (name,)}
    return {'spec': json.dumps(spec_dict)}


l3_col_url = '/roots/root1/level1s/level1_1/level2s/level2_1/level3s'
l3_item_url = '/'.join((l3_col_url, 'level3_1'))

Params = namedtuple('Params',
                    ['request', 'url', 'status_code', 'correct_data'])


class ParamsFactory(object):
    def __init__(self, session_modifier, rule, url,
                 status_code, correct_data, handler_maker, methods, *args,
                 **kwargs):
        self.c = client(
                methods=methods, handler_maker=handler_maker, s=session(),
                session_modifier=session_modifier, rule=rule, *args, **kwargs
        )
        self.ps = Params(
                self.c.get,
                url,
                status_code,
                correct_data
        )


l3_query = partial(query, model_to_query=Level3,
                   query_modifiers=query_modifiers()[Level3])

child_query = partial(
    query,
    model_to_query=Child,
    query_modifiers=child_collection_query_modifiers,
)


class BasicGetParams(ParamsFactory):
    def __init__(self, session_modifier, rule, url, status_code, correct_data,
                 handler_maker, *args, **kwargs):
        super(BasicGetParams, self).__init__(
                session_modifier=session_modifier,
                rule=rule,
                url=url,
                status_code=status_code,
                correct_data=correct_data,
                handler_maker=handler_maker,
                methods=['GET'],
                *args,
                **kwargs
        )


class BasicChildCollectionParams(BasicGetParams):
    def __init__(self, session_modifier, status_code, correct_data,
                 handler_maker, *args, **kwargs):
        super(BasicChildCollectionParams, self).__init__(
                session_modifier=session_modifier,
                rule='/parents/<level_0_id>/children',
                url='/parents/1/children',
                status_code=status_code,
                correct_data=correct_data,
                handler_maker=handler_maker,
                *args, **kwargs)


class NonEmptyChildCollectionParams(BasicChildCollectionParams):
    def __init__(self, *args, **kwargs):
        super(NonEmptyChildCollectionParams, self).__init__(
                session_modifier=parent_with_child,
                status_code=200,
                correct_data={'items': []},
                handler_maker=lambda s: get_handler(
                        partial(
                                get_collection,
                                s,
                                child_query,
                                partial(serialize_collection,
                                        create_schema(Child)())
                        )
                ),
                *args,
                **kwargs
        )


class EmptyChildCollectionParams(BasicChildCollectionParams):
    def __init__(self, *args, **kwargs):
        super(EmptyChildCollectionParams, self).__init__(
                session_modifier=parent_child,
                status_code=200,
                correct_data={'items': []},
                handler_maker=lambda s: get_handler(
                    partial(
                        get_collection,
                        s,
                        child_query,
                        partial(serialize_collection, create_schema(Child)())
                    )
                ),
                *args, **kwargs)


class BasicCollectionParams(BasicGetParams):
    def __init__(self, session_modifier, correct_data):
        status_code = 200
        url = l3_col_url
        rule = level3_collection_rule
        handler_maker = lambda s: get_handler(
                partial(
                        get_collection,
                        s,
                        l3_query,
                        partial(serialize_collection,
                                create_schema(Level3)())
                ),
                {'by_name': by_name_spec}
        )
        super(BasicCollectionParams, self).__init__(
                handler_maker=handler_maker,
                session_modifier=session_modifier,
                rule=rule,
                url=url,
                status_code=status_code,
                correct_data=correct_data,
        )


class GetCollectionEmptyParams(BasicCollectionParams):
    def __init__(self):
        super(GetCollectionEmptyParams, self).__init__(
            session_modifier=l3_empty,
            correct_data={'items': []}
        )


class GetCollectionCursoredParams(BasicCollectionParams):
    def __init__(self):
        super(GetCollectionCursoredParams, self).__init__(
            session_modifier=hundred_roots_elements,
            correct_data={
                'items': [
                    {'name': 'foo10'},
                    {'name': 'foo11'},
                ],
                'count': 2,
                'total': 100

            }
        )
        r = partial(self.c.get, query_string={'size': 2, 'page': 6})
        self.ps = self.ps._replace(request=r)


class GetCollectionNonEmptyParams(BasicCollectionParams):
    def __init__(self):
        session_modifier = l3_non_empty
        correct_data = {'items': [{'name': 'level3_1'}]}
        super(GetCollectionNonEmptyParams, self).__init__(session_modifier,
                                                          correct_data)


class SearchCollectionParams(BasicCollectionParams):
    def __init__(self):
        session_modifier = search_session
        correct_data = {'items': [{'name': 'find_me'}]}
        super(SearchCollectionParams, self).__init__(session_modifier,
                                                     correct_data)
        self.ps = self.ps._replace(request=partial(self.ps.request,
                                                   query_string=search_dict(
                                                           'find_me')))


class EmptySearchCollectionParams(BasicCollectionParams):
    def __init__(self):
        session_modifier = search_session
        correct_data = {'items': []}
        super(EmptySearchCollectionParams, self).__init__(session_modifier,
                                                          correct_data)
        self.ps = self.ps._replace(request=partial(self.ps.request,
                                                   query_string=search_dict(
                                                           'cannot_find_me')))


class BasicItemParams(BasicGetParams):
    def __init__(self, session_modifier, status_code, correct_data):
        rule = level3_item_rule
        url = l3_item_url
        handler_maker = lambda s: create_handler(
                partial(
                        get_item,
                        s,
                        l3_query,
                        partial(serialize_item,
                                create_schema(Level3)())
                )
        )
        super(BasicItemParams, self).__init__(
                session_modifier=session_modifier,
                rule=rule,
                url=url,
                status_code=status_code,
                correct_data=correct_data,
                handler_maker=handler_maker,
        )


class EmptyItemParams(BasicItemParams):
    def __init__(self):
        super(EmptyItemParams, self).__init__(
                session_modifier=l3_empty,
                status_code=404,
                correct_data=None
        )


class NonEmptyItemParams(BasicItemParams):
    def __init__(self):
        super(NonEmptyItemParams, self).__init__(
                session_modifier=l3_non_empty,
                status_code=200,
                correct_data={'name': 'level3_1'}
        )


@pytest.mark.parametrize('r,url,status_code,correct_data', [
    GetCollectionEmptyParams().ps,
    GetCollectionNonEmptyParams().ps,
    SearchCollectionParams().ps,
    EmptySearchCollectionParams().ps,
    EmptyItemParams().ps,
    NonEmptyItemParams().ps,
    EmptyChildCollectionParams().ps,
    NonEmptyChildCollectionParams().ps,
    GetCollectionCursoredParams().ps,
])
def test_get(r, url, status_code, correct_data):
    response = r(url)
    assert response.status_code == status_code
    if correct_data:
        assert json.loads(response.data) == correct_data


def test_delete_simple(session):
    c = client(
            handler_maker=lambda s: create_handler(
                    partial(delete_item, s, l3_query)
            ),
            methods=['DELETE'],
            session_modifier=l3_non_empty,
            rule=level3_item_rule,
            s=session
    )
    response = c.delete(l3_item_url)
    assert response.status_code == 200
    assert len(session.query(Level3).all()) == 0


def test_delete_many_to_many(session):
    c = client(
            handler_maker=lambda s: create_handler(
                    partial(delete_many_to_many,
                            s,
                            partial(
                                query,
                                model_to_query=Child,
                                query_modifiers=(
                                    (
                                        partial(filter_, Child.id),
                                    ),
                                )
                            ),
                            partial(
                                query,
                                model_to_query=Parent,
                                query_modifiers=(
                                    (
                                        partial(filter_, Parent.id),
                                    ),
                                )
                            ),
                            'children',
                            )

            ),
            methods=['DELETE'],
            session_modifier=parent_with_child,
            rule='/parents/<level_0_id>/children/<level_1_id>',
            s=session
    )
    adam, cain = load_family(session)
    response = c.delete('/parents/' + str(adam.id) + '/children/1')
    assert response.status_code == 200
    adam, cain = load_family(session)
    assert len(adam.children) == 0
    assert len(cain.parents) == 0


def load_family(ses):
    adam = ses.query(Parent).filter_by(name='Adam').one()
    cain = ses.query(Child).filter_by(name='Cain').one()
    return adam, cain


def test_post_root(session):
    c = client(
            handler_maker=lambda s: data_handler(
                    partial(
                            post_item,
                            s,
                            'name',
                            root_adder,
                            partial(deserialize_item,
                                    create_schema(Root)(), s)
                    )
            ),
            methods=['POST'],
            session_modifier=l0_empty,
            rule='/roots',
            s=session,
    )
    response = post_json(c, '/roots', {'name': 'root_1'})
    assert response.status_code == 200
    roots = session.query(Root).all()
    assert len(roots) == 1
    assert roots[0].name == 'root_1'


def test_post_non_root(session):
    q = partial(query, model_to_query=Level2, query_modifiers=query_modifiers()[Level2])
    c = client(
            handler_maker=lambda s: data_handler(
                    partial(
                            post_item,
                            s,
                            'name',
                            partial(non_root_adder, q, 'level3s'),
                            partial(deserialize_item,
                                    create_schema(Level3)(), s)
                    )
            ),
            methods=['POST'],
            session_modifier=l3_empty,
            rule=level3_collection_rule,
            s=session,
    )
    response = post_json(c, l3_col_url, {'name': 'level3_1'})
    assert response.status_code == 200
    l3s = session.query(Level2).one().level3s
    assert len(l3s) == 1
    assert l3s[0].name == 'level3_1'


def test_post_many_to_many(session):
    iq = partial(
            query,
            model_to_query=Child,
            query_modifiers=(
                (
                    partial(filter_, Child.id),
                ),
            )
    )
    pq = partial(
            query,
            model_to_query=Parent,
            query_modifiers=(
                (
                    partial(filter_, Parent.id),
                ),
            )
    )
    c = client(
            handler_maker=lambda s: data_handler(
                    partial(
                            post_item_many_to_many,
                            s,
                            iq,
                            pq,
                            'children'
                    )
            ),
            methods=['POST'],
            session_modifier=parent_child,
            rule='/parents/<level_0_id>/children',
            s=session,
    )
    adam, cain = load_family(session)
    response = post_json(c, '/parents/' + str(adam.id) + '/children',
                         {'id': cain.id})
    assert response.status_code == 200
    adam, cain = load_family(session)
    assert cain in adam.children
    assert adam in cain.parents


def test_patch(session):
    c = client(
        handler_maker=lambda s: data_handler(
            partial(
                    patch_item,
                    s,
                    l3_query,
            )
        ),
        methods=['PATCH'],
        session_modifier=l3_non_empty,
        rule=level3_item_rule,
        s=session,
    )
    response = patch(c, l3_item_url, {'name': 'l3_new_name'})
    assert response.status_code == 200
    l3s = session.query(Level3).filter_by(name='level3_1').all()
    assert len(l3s) == 0
    l3s = session.query(Level3).filter_by(name='l3_new_name').all()
    assert len(l3s) == 1



