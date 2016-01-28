from collections import namedtuple, defaultdict
from functools import partial
from itertools import chain

from rest.handlers import get_item, post_item, \
    get_collection, \
    serialize_item, serialize_collection, deserialize_item, \
    schema_maker, post_item_many_to_many, delete_item, \
    create_handler, \
    request_data_wrapper, get_handler, delete_many_to_many, root_adder, \
    patch_item
from rest.helpers import identity
from rest.hierarchy_traverser import all_paths, create_graph
from rest.introspect import pk_attr_name
from rest.query import query, filter_, join

EndpointParams = namedtuple('EndpointParams',
                            ['rule', 'endpoint', 'view_func', 'methods'])


# This class could be used instead of dict to simplify testing a little
# Or when api for config will be fixed
class Config(object):
    def __init__(self, url_name, item_serializer, collection_serializer,
                 item_deserializer, attr_to_use_in_url):
        self.attr_to_use_in_url = attr_to_use_in_url
        self.item_deserializer = item_deserializer
        self.collection_serializer = collection_serializer
        self.item_serializer = item_serializer
        self.url_name = url_name

    def __eq__(self, other):
        if not isinstance(self, other):
            return False
        return True


def endpoints_params(endpoints):
    es = chain.from_iterable(
            map(
                    lambda d: d.items(),
                    chain.from_iterable(
                            map(lambda x: x.values(), endpoints)
                    )
            )
    )
    return [EndpointParams(
            rule=rh[0],
            endpoint=rh[0] + method,
            view_func=rh[1],
            methods=[method]
    )
            for method, rh in es]


def create_query_modifiers(graph, config, ch_m, p_m):
    im = partial(filter_, getattr(ch_m, config[ch_m]['exposed_attr']))
    if (ch_m, p_m) in graph.edges():
        jm = partial(join, p_m, graph[ch_m][p_m]['rel_attr'])
        return im, jm
    else:
        return im,


def endpoints_for_path(path, config, db_session, graph):
    col_rule, item_rule = url_rules_for_path(path[1:], config)
    model = path[-1]
    parent = path[-2]

    ps = list(reversed(path))
    query_modifiers = tuple((create_query_modifiers(graph, config, ch_m, p_m)
                             for ch_m, p_m in zip(ps, ps[1:])))
    q = partial(
            query,
            model_to_query=model,
            query_modifiers=query_modifiers,
    )
    model_config = config[model]
    endpoints = defaultdict(dict)
    endpoints['collection']['GET'] = (
        col_rule, get_handler(
                partial(
                        get_collection,
                        db_session,
                        q,
                        model_config['collection_serializer'],
                ),
                model_config.get('specs', {})
        )
    )
    h = partial(
            post_item,
            db_session,
            model_config['exposed_attr'],
            root_adder,
            model_config['item_deserializer'],
    )

    del_h = partial(
            delete_item,
            db_session,
            q,
    )

    if parent:
        rel_attr = graph[parent][model]['rel_attr']
        item_query = partial(
                query,
                model_to_query=model,
                query_modifiers=(
                    (
                        partial(filter_, getattr(model,
                                                 model_config[
                                                     'exposed_attr'])),
                    ),
                )
        )
        parent_query = partial(
                            query,
                            model_to_query=parent,
                            query_modifiers=query_modifiers[1:]
                    )
        if (model, parent) in graph.edges():
            h = partial(
                    post_item_many_to_many,
                    db_session,
                    item_query,
                    parent_query,
                    rel_attr,
            )
            del_h = partial(
                    delete_many_to_many,
                    db_session,
                    item_query,
                    parent_query,
                    rel_attr)
    endpoints['collection']['POST'] = (
        col_rule, request_data_wrapper(h)
    )
    endpoints['item']['GET'] = (
        item_rule, create_handler(
                partial(
                        get_item,
                        db_session,
                        q,
                        model_config['item_serializer']
                )
        )
    )
    endpoints['item']['PATCH'] = (
        item_rule, request_data_wrapper(
            partial(
                patch_item,
                db_session,
                q,
            )
        )
    )
    endpoints['item']['DELETE'] = (
        item_rule, create_handler(del_h)
    )
    return model, endpoints


def register_handlers(app, endpoint_params):
    for ep in endpoint_params:
        app.add_url_rule(**ep._asdict())


def default_config(models, db_session=None):
    return {m: default_cfg_for_model(m, db_session) for m in models}


def create_api(root_model, db_session, app,
               config_decorator=identity,
               graph_decorator=identity,
               endpoints_decorator=identity):
    graph = graph_decorator(create_graph(root_model))
    config = config_decorator(default_config(graph.nodes(), db_session))
    all_ps = list(reversed(all_paths(graph, root_model)))
    params = [endpoints_for_path([None] + path, config, db_session, graph)
              for path in all_ps]
    d = dict(params)
    eps = endpoints_params(endpoints_decorator(d.values()))
    register_handlers(app, eps)


def defaults_for_root(root_model, db_session):
    graph = create_graph(root_model)
    default_conf = default_config(graph.nodes(), db_session)
    return graph, default_conf


def serializers_maker(model, schema_factory, db_session):
    schema = schema_factory(model)()
    item_serializer = partial(serialize_item, schema)
    collection_serializer = partial(serialize_collection, schema)
    item_deserializer = partial(deserialize_item, schema, db_session)
    return item_serializer, collection_serializer, item_deserializer


def default_cfg_for_model(model, db_session):
    i_ser, col_ser, i_des = serializers_maker(
            model, schema_maker, db_session)
    return {
        'url_name': model.__tablename__,
        'item_serializer': i_ser,
        'collection_serializer': col_ser,
        'item_deserializer': i_des,
        'exposed_attr': pk_attr_name(model)[0],
        'exposed_attr_type': 'int:' if pk_attr_name(model)[1] == int else '',
        'specs': {},
    }


def url_rules_for_path(path, config):
    url_parts = [''] + list(chain(
            *[[config[model]['url_name'],
               '<{}level_{}_id>'.format(config[model]['exposed_attr_type'], i)]
              for i, model in enumerate(path)]
    )
    )
    collection_resource_url = '/'.join(url_parts[:-1])
    item_resource_url = '/'.join(url_parts)
    return collection_resource_url, item_resource_url
