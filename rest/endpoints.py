from collections import defaultdict, namedtuple
from copy import deepcopy
from functools import partial, reduce
from itertools import chain

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
    patch_item,
    post_item,
    post_item_many_to_many,
    root_adder,
    non_root_adder,
    schemas_handler,
    serialize_collection,
    serialize_item,
)
from rest.helpers import identity, list_dict, merge
from rest.hierarchy_traverser import all_paths, create_graph
from rest.introspect import pk_attr_name
from rest.query import filter_, join, query
from rest.schema import to_jsonschema
from sqlalchemy.orm.base import MANYTOMANY


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
    return [EndpointParams(
        rule=rh[0],
        endpoint=rh[0] + method,
        view_func=rh[1],
        methods=[method]
    )
            for eps in endpoints
            for j in eps.values()
            for method, rh in j.iteritems()]


def schemas_for_paths(paths, config, graph):
    all_models = set(list(chain.from_iterable(paths)))
    schemas = {m: to_jsonschema(config[m]['schema']) for m in all_models}
    model_relation_pairs = chain.from_iterable([zip(p, p[1:]) for p in paths])
    by_model = list_dict(model_relation_pairs)
    root = paths[0][0]
    print(root)

    for m, s in schemas.iteritems():
        s['links'] = reduce(
            partial(
                make_link,
                graph,
                m
            ),
            list(set(by_model[m])),
            []
        )
    schemas[root]['links'].append(
        {
            'rel': 'self',
            'href': '/'.join(('', config[root]['url_name'])),
            'schema_key': root
        }
    )
    return schemas


def make_link(graph, model, links, relation):
    links.append(
        {
            'rel': graph[model][relation]['rel_attr'],
            'href': '/'.join(('', '{id}', graph[model][relation]['rel_attr'])),
            'schema_key': relation,
        }
    )
    return links


def is_many_to_many(graph, model, parent):
    return ((model, parent) in graph.edges() and
            graph[model][parent]['rel_type'] == MANYTOMANY)


def create_query_modifiers(graph, config, ch_m, p_m):
    im = partial(filter_, getattr(ch_m, config[ch_m]['exposed_attr']))
    if is_many_to_many(graph, ch_m, p_m):
        jm = partial(join, p_m, graph[ch_m][p_m]['rel_attr'])
        return im, jm
    else:
        return im,


def query_modifiers_for_path(graph, config, path):
    return tuple((create_query_modifiers(graph, config, ch_m, p_m)
                  for ch_m, p_m in zip(path, path[1:])))


def apis_for_path(path, config, db_session, graph):
    col_rule, item_rule = url_rules_for_path(path[1:], config)
    model = path[-1]
    parent = path[-2]

    ps = list(reversed(path))
    query_modifiers = query_modifiers_for_path(graph, config, ps)
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
        if is_many_to_many(graph, model, parent):
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
        else:
            h = partial(
                post_item,
                db_session,
                model_config['exposed_attr'],
                partial(
                    non_root_adder,
                    parent_query,
                    rel_attr,
                ),
                model_config['item_deserializer'],
            )
    endpoints['collection']['POST'] = (
        col_rule, data_handler(h)
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
        item_rule, data_handler(
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


def register_all_apis(app, schemas, all_apis):
    endpoints = chain.from_iterable(
        (api.values() for api in all_apis)
    )
    eps = endpoints_params(chain.from_iterable(endpoints))
    out_schemas = deepcopy(reduce(merge, schemas, {}))
    for schema in out_schemas.values():
        for l in schema['links']:
            l['schema_key'] = str(l['schema_key'])
    eps.append(
        EndpointParams(
            rule='/schemas',
            endpoint='schemas',
            view_func=partial(
                schemas_handler,
                {str(m): schema for m, schema in out_schemas.iteritems()}
            ),
            methods=['GET']
        )
    )
    register_handlers(app, eps)


def create_api(root_model, db_session,
               config_decorator=identity,
               graph_decorator=identity,
               paths_decorator=identity):
    graph = graph_decorator(create_graph(root_model))
    config = config_decorator(default_config(graph.nodes(), db_session))
    ps = tuple(paths_decorator(all_paths(graph, root_model)))
    all_ps = tuple(reversed(ps))
    apis = [apis_for_path((None,) + path, config, db_session, graph)
            for path in all_ps]
    apis_by_model = list_dict(apis)
    schemas = schemas_for_paths(ps, config, graph)
    return apis_by_model, schemas


def my_getitem(index, list_):
    return list_[index]


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
        model, create_schema, db_session)
    return {
        'url_name': model.__tablename__,
        'item_serializer': i_ser,
        'schema': create_schema(model),
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
