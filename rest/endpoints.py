from collections import namedtuple, defaultdict
from functools import partial
from itertools import chain

from rest.handlers import get_item, post_item, \
    get_collection, \
    serialize_item, serialize_collection, deserialize_item, \
    schema_class_for_model, post_item_many_to_many, delete_item, \
    create_handler, \
    post_handler, get_handler
from rest.hierarchy_traverser import all_paths, create_graph
from rest.introspect import pk_attr_name

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


def endpoints_for_path(path, config, db_session, graph):
    col_rule, item_rule = url_rules_for_path(path, config)
    ps = reversed_paths(path, config)
    model = path[-1]
    model_config = config[model]
    endpoints = defaultdict(dict)
    endpoints['collection']['GET'] = (
        col_rule, get_handler(
                partial(
                        get_collection,
                        db_session,
                        ps,
                        model_config['collection_serializer']
                )
        )
    )

    def is_many_to_many():
        return (path[-1], path[-2]) in graph.edges()

    if len(path) == 1:
        h = partial(
                post_item,
                db_session,
                ps,
                None,
                model_config['item_deserializer']
        )
    else:
        rel_attr = graph[path[-2]][path[-1]]['rel_attr']
        if is_many_to_many():
            h = partial(
                    post_item_many_to_many,
                    db_session,
                    ps,
                    rel_attr
            )
        else:
            h = partial(
                    post_item,
                    db_session,
                    ps,
                    rel_attr,
                    model_config['item_deserializer']
            )
    endpoints['collection']['POST'] = (
        col_rule, post_handler(h)
    )
    endpoints['item']['GET'] = (
        item_rule, create_handler(
                partial(
                        get_item,
                        db_session,
                        ps,
                        model_config['item_serializer']
                )
        )
    )
    endpoints['item']['DELETE'] = (
        item_rule, create_handler(
                partial(
                        delete_item,
                        db_session,
                        ps
                )
        )
    )
    return model, endpoints


def reversed_paths(path, config):
    return [(m, config[m]['exposed_attr']) for m in reversed(path)]


def register_handlers(app, endpoint_params):
    for ep in endpoint_params:
        app.add_url_rule(**ep._asdict())


def default_config(models, db_session=None):
    return {m: default_cfg_for_model(m, db_session) for m in models}


def identity(x):
    return x


def create_api(root_model, db_session, app,
               config_decorator=identity,
               graph_decorator=identity,
               endpoints_decorator=identity):
    graph = graph_decorator(create_graph(root_model))
    config = config_decorator(default_config(graph.nodes(), db_session))
    params = [endpoints_for_path(p, config, db_session, graph)
              for p in all_paths(graph, root_model)]
    d = dict(params)
    eps = endpoints_params(endpoints_decorator(d.values()))
    register_handlers(app, eps)


def defaults_for_root(root_model, db_session):
    graph = create_graph(root_model)
    default_conf = default_config(graph.nodes(), db_session)
    return graph, default_conf


def default_cfg_for_model(model, db_session=None):
    schema = schema_class_for_model(model)()
    return {
        'url_name': model.__tablename__,
        'item_serializer': partial(serialize_item, schema),
        'collection_serializer': partial(serialize_collection, schema),
        'item_deserializer': partial(
                deserialize_item,
                schema,
                db_session
        ),
        'exposed_attr': pk_attr_name(model)[0],
        'exposed_attr_type': 'int:' if pk_attr_name(model)[1] == int else ''
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
