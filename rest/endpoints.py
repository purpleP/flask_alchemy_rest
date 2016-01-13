from collections import namedtuple
from functools import partial
from itertools import chain

from rest.handlers import get_collection_item, post_flask_wrapper, post_item, get_collection, \
    serialize_item, serialize_collection, deserialize_item, schema_class_for_model
from rest.hierarchy_traverser import all_paths
from rest.introspect import pk_attr_name

EndpointParams = namedtuple('EndpointParams', ['rule', 'endpoint', 'view_func', 'methods'])


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


def register_handlers(graph, root, config, db_session, app):
    params = [endpoint_params_for_path(list(p), config, db_session, graph)
              for p in all_paths(graph, root)]
    [register_handler(app, endpoint_param) for endpoint_param in params]


def register_handler(app, endpoint_params):
    app.add_url_rule(**endpoint_params)


def default_config(models, db_session=None):
    return {m: default_cfg_for_model(m, db_session) for m in models}


def default_cfg_for_model(model, db_session=None):
    schema = schema_class_for_model(model)()
    return {
        'url_name': model.__tablename__,
        'item_serializer': partial(serialize_item, schema),
        'collection_serializer': partial(serialize_collection, schema),
        'item_deserializer': partial(
                deserialize_item,
                schema_class_for_model(model),
                db_session
        ),
        'attr_to_use_in_url': pk_attr_name(model)
    }


def endpoint_params_for_path(path, config, db_session, graph):
    collection_path, item_path = urls_for_path(path, config)
    query_params = params_from_path(graph, path)
    model_cfg = config[path[-1]]
    return (
        get_collection_params(collection_path, db_session, model_cfg, query_params),
        get_collection_item_params(item_path, db_session, model_cfg, query_params),
        post_item_params(collection_path, db_session, model_cfg, query_params),
    )


def get_collection_item_params(item_path, db_session, model_config, query_params):
    return EndpointParams(
            rule=item_path,
            endpoint=item_path,
            view_func=partial(
                    get_collection_item,
                    db_session,
                    query_params,
                    model_config['item_serializer']
            ),
            methods=['GET']
    )


def post_item_params(collection_path, db_session, model_config, query_params):
    return EndpointParams(
            rule=collection_path,
            endpoint=collection_path + 'post',
            view_func=partial(
                    post_flask_wrapper,
                    partial(
                            post_item,
                            db_session,
                            query_params,
                            model_config['item_deserializer'],
                            model_config['attr_to_use_in_url'],
                    )
            ),
            methods=['POST']
    )


def get_collection_params(collection_path, db_session, model_config, query_params):
    return EndpointParams(
            rule=collection_path,
            endpoint=collection_path,
            view_func=partial(
                    get_collection,
                    db_session,
                    query_params,
                    model_config['collection_serializer']
            ),
            methods=['GET']
    )


def get_fk_name(graph, parent, child):
    if child:
        return graph[parent][child]['rel'].fk_attr_name
    else:
        return None


def urls_for_path(path, config):
    url_parts = [''] + list(chain(
            *[[config[model]['url_name'], '<level_{}_id>'.format(i)]
              for i, model in enumerate(path)]
    )
    )
    collection_resource_url = '/'.join(url_parts[:-1])
    item_resource_url = '/'.join(url_parts)
    return collection_resource_url, item_resource_url


def get_attr_name(graph, parent, child):
    try:
        return graph[parent][child]['rel'].fk_linked_attr_name
    except KeyError:
        return None
