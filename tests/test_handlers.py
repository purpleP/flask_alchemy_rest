import json
from collections import namedtuple
from functools import partial
from itertools import izip, chain

import pytest
from flask import Flask
from rest.handlers import (
    create_handler,
    create_schema,
    delete_item,
    delete_many_to_many,
    get_collection,
    get_handler,
    data_handler,
    get_item,
    post_item,
    post_item_many_to_many,
    root_adder,
    non_root_adder,
    serialize_collection,
    deserialize_item,
    serialize_item,
)
from tests.flask_test_helpers import post_json
from rest.helpers import inits
from rest.query import query
from tests.fixtures import (
    Child,
    Level1,
    Level2,
    Level3,
    Parent,
    Root,
    circular_full_data,
    hierarchy_full_data,
    level3_collection_rule,
    level3_item_rule,
    session,
)


def by_name_spec(name, query):
    return query.filter_by(name=name)


State = namedtuple('State', ['session', 'client'])


def client(params, session_modifier):
    sess = session()
    session_modifier(sess)
    sess.commit()
    app = Flask('foo')
    app.debug = True
    app.add_url_rule(
        rule=params[0],
        endpoint='1',
        view_func=params[1](sess),
        methods=params[2]
    )
    return State(sess, app.test_client())


def search_dict(name):
    spec_dict = {'name': 'by_name', 'args': (name,)}
    return {'spec': json.dumps(spec_dict)}


def make_url(collection_names, item_names):
    full_item_names = ('_'.join(ins) for ins in inits(item_names)[1:])
    url_parts = ('/'.join(pair)
                 for pair in izip(collection_names, full_item_names))
    if len(collection_names) > len(item_names):
        full_parts = chain(('',), url_parts, (collection_names[-1],))
    else:
        full_parts = chain(('',), url_parts)
    url = '/'.join(full_parts)
    return url


l3_query = partial(
    query,
    model_to_query=Level3,
    join_attrs=(Level2, Level1, Root),
    attrs_to_filter=(
        Level3.name,
        Level2.name,
        Level1.name,
        Root.name
    )
)

l3_col_query = partial(
    query,
    model_to_query=Level3,
    join_attrs=(Level2, Level1, Root),
    attrs_to_filter=(Level2.name, Level1.name, Root.name)
)

l2_item_query = partial(
    query,
    model_to_query=Level2,
    join_attrs=(Level1, Root),
    attrs_to_filter=(Level2.name, Level1.name, Root.name)
)


def root_post_item_handler_maker(session):
    return data_handler(
        partial(
            post_item,
            session,
            'name',
            root_adder,
            partial(deserialize_item, create_schema(Root)(), session)
        )
    )


def post_state_checker(state, model, name_):
    assert state.session.query(model).filter_by(name=name_).count() == 1


def l3_post_item_handler_maker(session):
    return data_handler(
        partial(
            post_item,
            session,
            'name',
            partial(
                non_root_adder,
                l2_item_query,
                'level3s',
            ),
            partial(deserialize_item, create_schema(Level3)(), session)
        )
    )


parent_query = partial(
    query,
    model_to_query=Parent,
    join_attrs=(Parent,),
    attrs_to_filter=(Parent.name)
)

child_query = partial(
    query,
    model_to_query=Child,
    attrs_to_filter=(
        Child.name,
    )
)


def post_many_to_many_handler_maker(session):
    return data_handler(
        partial(
            post_item_many_to_many,
            session,
            child_query,
            parent_query,
            'children'
        )
    )


post_many_to_many_params = (
    '/parents/<level_0_id>/children',
    post_many_to_many_handler_maker,
    ['POST']
)


def post_many_to_many_checker(state):
    assert state.session.query(Child) \
            .join(Child, Parent.children) \
            .filter(Parent.name == 'pseudoroot_1_parent_1') \
            .filter(Child.name == 'pseudoroot_1_child_0').count() == 1


root_post_params = (
    '/roots',
    root_post_item_handler_maker,
    ['POST']
)

l3_post_params = (
    level3_collection_rule,
    l3_post_item_handler_maker,
    ['POST']
)


def l3_collection_handler_maker(session):
    return get_handler(
        partial(
            get_collection,
            session,
            l3_col_query,
            partial(serialize_collection, create_schema(Level3)())
        ),
        {'by_name': by_name_spec}
    )


l3_collection_params = (
    level3_collection_rule,
    l3_collection_handler_maker,
    ['GET']
)


def l3_item_handler_maker(session):
    return create_handler(
        partial(
            get_item,
            session,
            l3_query,
            partial(serialize_item, create_schema(Level3)())
        ),
    )


l3_item_params = (
    level3_item_rule,
    l3_item_handler_maker,
    ['GET']
)


def l3_delete_handler_maker(session):
    return create_handler(
        partial(
            delete_item,
            session,
            l3_query,
        )
    )


l3_delete_params = (
    level3_item_rule,
    l3_delete_handler_maker,
    ['DELETE']
)

child_query = partial(
    query,
    model_to_query=Child,
    join_attrs=(Child, Parent.children),
    attrs_to_filter=(
        Child.name,
        Parent.name
    )
)

parent_query = partial(
    query,
    model_to_query=Parent,
    join_attrs=(Parent, Child.parents),
    attrs_to_filter=(
        Parent.name,
    )
)


def child_delete_handler_maker(session):
    return create_handler(
        partial(
            delete_many_to_many,
            session,
            child_query,
            parent_query,
            'children'
        )
    )


child_delete_params = (
    '/parents/<level_0_id>/children/<level_1_id>',
    child_delete_handler_maker,
    ['DELETE']
)


def get(client, url, *args, **kwargs):
    return client.get(url, *args, **kwargs)


def delete(client, url, *args, **kwargs):
    return client.delete(url, *args, **kwargs)


def check_if_deleted(state, _id):
    assert state.session \
               .query(Level3) \
               .filter(Level3.name.in_((_id,))).all() == []


def check_if_many_to_many_deleted(state, parent_id, child_id):
    assert state.session.query(Child) \
               .join(Child, Parent.children) \
               .filter(Parent.name == parent_id) \
               .filter(Child.name == child_id).all() == []


@pytest.mark.parametrize('state,req,status_code,correct_data,state_checker', [
    (
        client(l3_collection_params, hierarchy_full_data),
        partial(
            get,
            url=make_url(
                collection_names=(
                    'roots', 'level1s', 'level2s', 'level3s'),
                item_names=('root_1', 'level1_1', 'level2_1')
            )
        ),
        200,
        {
            'items': [
                {'name': 'root_1_level1_1_level2_1_level3_0'},
                {'name': 'root_1_level1_1_level2_1_level3_1'},
            ]
        },
        None
    ),
    (
        client(l3_item_params, hierarchy_full_data),
        partial(
            get,
            url=make_url(
                collection_names=(
                    'roots', 'level1s', 'level2s', 'level3s'),
                item_names=('root_1', 'level1_1', 'level2_1', 'level3_0')
            )
        ),
        200,
        {'name': 'root_1_level1_1_level2_1_level3_0'},
        None
    ),
    (
        client(l3_item_params, hierarchy_full_data),
        partial(
            get,
            url=make_url(
                collection_names=(
                    'roots', 'level1s', 'level2s', 'level3s'),
                item_names=('root_1', 'level1_1', 'level2_1', 'level3_2')
            )
        ),
        404,
        None,
        None
    ),
    (
        client(l3_delete_params, hierarchy_full_data),
        partial(
            delete,
            url=make_url(
                collection_names=(
                    'roots', 'level1s', 'level2s', 'level3s'),
                item_names=('root_1', 'level1_1', 'level2_1', 'level3_0')
            )
        ),
        200,
        None,
        partial(check_if_deleted, _id='level3_0')
    ),
    (
        client(l3_delete_params, hierarchy_full_data),
        partial(
            delete,
            url=make_url(
                collection_names=(
                    'roots', 'level1s', 'level2s', 'level3s'),
                item_names=('root_1', 'level1_1', 'level2_1', 'level3_2')
            )
        ),
        404,
        None,
        None
    ),
    (
        client(child_delete_params, circular_full_data),
        partial(
            delete,
            url='/parents/pseudoroot_1_parent_1/children/pseudoroot_1_child_1'
        ),
        200,
        None,
        partial(
            check_if_many_to_many_deleted,
            parent_id='pseudoroot_1_parent_1',
            child_id='pseudoroot_1_child_1'
        )
    ),
    (
        client(root_post_params, hierarchy_full_data),
        partial(
            post_json,
            url='/roots',
            data={'name': 'root_2'},
        ),
        200,
        {'id': 'root_2'},
        partial(post_state_checker,
                model=Root,
                name_='root_2')
    ),
    (
        client(l3_post_params, hierarchy_full_data),
        partial(
            post_json,
            url=make_url(
                collection_names=(
                    'roots', 'level1s', 'level2s', 'level3s'),
                item_names=('root_1', 'level1_1', 'level2_1')
            ),
            data={'name': 'root_1_level1_1_level2_1_level3_2'},
        ),
        200,
        {'id': 'root_1_level1_1_level2_1_level3_2'},
        partial(post_state_checker,
                model=Level3,
                name_='root_1_level1_1_level2_1_level3_2')
    ),
    (
        client(post_many_to_many_params, circular_full_data),
        partial(
            post_json,
            url='/parents/pseudoroot_1_parent_1/children',
            data={'id': 'pseudoroot_1_child_0'}
        ),
        200,
        None,
        post_many_to_many_checker
    ),
])
def test_handler(state, req, status_code, correct_data, state_checker):
    response = req(state.client)
    assert response.status_code == status_code
    if correct_data:
        assert json.loads(response.data) == correct_data
    if state_checker is not None:
        state_checker(state=state)

# TODO test_patch
# TODO test post many_to_many and non root
# for correct error if nothing is found

    # def test_patch(session):
    # c = client(
    # handler_maker=lambda s: data_handler(
    # partial(
    # patch_item,
    # s,
    # l3_query,
    # )
    # ),
    # methods=['PATCH'],
    # session_modifier=l3_non_empty,
    # rule=level3_item_rule,
    # s=session,
    # )
    # response = patch(c, l3_item_url, {'name': 'l3_new_name'})
    # assert response.status_code == 200
    # l3s = session.query(Level3).filter_by(name='level3_1').all()
    # assert len(l3s) == 0
    # l3s = session.query(Level3).filter_by(name='l3_new_name').all()
    # assert len(l3s) == 1
