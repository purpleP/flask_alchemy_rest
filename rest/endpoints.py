from collections import namedtuple, defaultdict
from functools import partial
from itertools import chain

from rest.handlers import get_item, post_item, \
    get_collection, \
    serialize_item, serialize_collection, deserialize_item, \
    schema_maker, post_item_many_to_many, delete_item, \
    create_handler, \
    post_handler, get_handler, delete_many_to_many
from rest.helpers import identity
from rest.hierarchy_traverser import all_paths, create_graph
from rest.introspect import pk_attr_name
from rest.query import query, any_criterion, eq_criterion

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


def create_criteria(graph, config, child_model, parent_model):
    parent_criteria = ()
    if parent_model:
        if (child_model, parent_model) in graph.edges():
            rel_attr = graph[child_model][parent_model]['rel_attr']
            parent_criteria = partial(
                    any_criterion,
                    getattr(child_model, rel_attr),
                    config[parent_model]['exposed_attr']
            )
        else:
            parent_criteria = partial(
                    eq_criterion,
                    getattr(parent_model, config[parent_model]['exposed_attr'])
            )
    else:
        parent_criteria = ()
    item_criteria = partial(
            eq_criterion,
            getattr(child_model, config[child_model]['exposed_attr'])
    )
    return parent_criteria, item_criteria


def endpoints_for_path(path, config, db_session, graph):
    col_rule, item_rule = url_rules_for_path(path[1:], config)
    model = path[-1]

    ps = list(reversed(path))
    criteria = [create_criteria(graph, config, ch_m, p_m)
                for ch_m, p_m in zip(ps, ps[1:])]
    model_config = config[model]
    endpoints = defaultdict(dict)
    endpoints['collection']['GET'] = (
        col_rule, get_handler(
                partial(
                        get_collection,
                        db_session,
                        partial(
                                query,
                                model_to_query=model,

                        ),
                        model_config['collection_serializer'],
                ),
                model_config.get('specs', {})
        )
    )

    if len(path) == 1:
        h = partial(
                post_item,
                db_session,
                ps,
                None,
                model_config['item_deserializer']
        )
        del_h = partial(
                delete_item,
                db_session,
                ps
        )
    else:
        rel_attr = graph[path[-2]][path[-1]]['rel_attr']
        if is_many_to_many():
            h = partial(post_item_many_to_many, db_session, ps, rel_attr)
            del_h = partial(delete_many_to_many, db_session, ps, rel_attr)
        else:
            h = partial(
                    post_item,
                    db_session,
                    ps,
                    rel_attr,
                    model_config['item_deserializer']
            )
            del_h = partial(delete_item, db_session, ps)
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
