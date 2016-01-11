from collections import namedtuple
from itertools import izip, chain

from pymonad import curry
from rest.query import Relationship, QueryParam, get_attr_name
from rest.handlers import get_collection_item, post_flask_wrapper, post_item, get_collection

EndpointParams = namedtuple('EndpointParams', ['rule', 'endpoint', 'view_func', 'methods'])


def register_handlers(app, path, config, db_session, graph, model_cfg):
    collection_path, item_path = urls_for_path(path, model_cfg)
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
            view_func=get_collection_item(
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
            view_func=post_flask_wrapper(
                    post_item(
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
            view_func=get_collection(
                    db_session,
                    query_params,
                    model_config['collection_serializer']
            ),
            methods=['GET']
    )


def params_from_path(graph, path):
    rev_path = list(reversed(path))
    relationships = [Relationship(prev, cur, next)
                     for (prev, cur, next) in
                     izip(chain([None], rev_path), rev_path, rev_path[1:])]

    return tuple(QueryParam(
            model=r.current_level,
            attr_name=get_attr_name(graph, r.current_level, r.previous_level),
            foreign_key_name=graph[r.next_level][r.current_level]['rel'].fk_attr_name,
            foreign_key_value=None
    )
                 for r in relationships)


@curry
def config_name_provider(config, model):
    return config[model]['url_name']


def urls_for_path(path, name_provider):
    url_parts = [''] + list(chain(
            *[[name_provider(model), '<level_{}_id>'.format(i)]
              for i, model in enumerate(path)]
    )
    )
    collection_resource_url = '/'.join(url_parts[:-1])
    item_resource_url = '/'.join(url_parts)
    return collection_resource_url, item_resource_url
