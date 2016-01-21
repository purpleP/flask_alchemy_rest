from collections import namedtuple
from functools import partial
from itertools import chain

from rest.handlers import get_item, flask_post_wrapper, post_item, \
    get_collection, \
    serialize_item, serialize_collection, deserialize_item, \
    schema_class_for_model, post_item_many_to_many, delete_item
from rest.hierarchy_traverser import all_paths, create_graph, inits, tails, \
    cycle_free_graphs
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


def endpoint_params_for_path(path, config, db_session, graph):
    col_rule, item_rule = url_rules_for_path(path, config)
    ps = reversed_paths(path, config)
    model_config = config[path[-1]]
    get_collection_params = EndpointParams(
            rule=col_rule,
            endpoint=col_rule + 'GET',
            view_func=partial(
                    get_collection,
                    db_session,
                    ps,
                    model_config['collection_serializer']
            ),
            methods=['GET']
    )
    get_item_params = EndpointParams(
            rule=item_rule,
            endpoint=item_rule + 'GET',
            view_func=partial(
                    get_item,
                    db_session,
                    ps,
                    model_config['item_serializer']
            ),
            methods=['GET']
    )
    delete_item_params = EndpointParams(
            rule=item_rule,
            endpoint=item_rule + 'DELETE',
            view_func=partial(
                    delete_item,
                    db_session,
                    ps
            ),
            methods=['DELETE']
    )
    # TODO make all nodes in graph to have identity arrow instead
    if len(path) == 1:
        rel_attr = None
        post_item_params = EndpointParams(
                rule=col_rule,
                endpoint=col_rule + 'POST',
                view_func=partial(
                        flask_post_wrapper,
                        partial(
                                post_item,
                                db_session,
                                ps,
                                rel_attr,
                                model_config['item_deserializer']
                        )
                ),
                methods=['POST']
        )
    else:
        rel_attr = graph[path[-2]][path[-1]]['rel_attr']
        if (path[-1], path[-2]) in graph.edges():
            post_item_params = EndpointParams(
                    rule=col_rule,
                    endpoint=col_rule + 'POST',
                    view_func=partial(
                            flask_post_wrapper,
                            partial(
                                    post_item_many_to_many,
                                    db_session,
                                    ps,
                                    rel_attr
                            )
                    ),
                    methods=['POST']
            )
        else:
            post_item_params = EndpointParams(
                    rule=col_rule,
                    endpoint=col_rule + 'POST',
                    view_func=partial(
                            flask_post_wrapper,
                            partial(
                                    post_item,
                                    db_session,
                                    ps,
                                    rel_attr,
                                    model_config['item_deserializer']
                            )
                    ),
                    methods=['POST']
            )
    return get_collection_params, get_item_params, \
           post_item_params, delete_item_params


def reversed_paths(path, config):
    return [(m, config[m]['exposed_attr']) for m in reversed(path)]


def register_handlers(graph, root, config, db_session, app):
    params = [endpoint_params_for_path(p, config, db_session, graph)
              for p in all_paths(graph, root)]

    [register_handler(app, endpoint_param) for endpoint_param in params]


def register_handler(app, endpoint_params):
    for ep in endpoint_params:
        app.add_url_rule(**ep._asdict())
        app.add_url_rule(**ep._asdict())
        app.add_url_rule(**ep._asdict())


def default_config(models, db_session=None):
    return {m: default_cfg_for_model(m, db_session) for m in models}


def create_default_api(root_model, db_session, app):
    graph, default_conf = defaults_for_root(root_model, db_session)
    register_handlers(graph, root_model, default_conf, db_session, app)


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
