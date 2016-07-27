from collections import defaultdict, namedtuple
from copy import deepcopy
from functools import partial, reduce
from itertools import chain
from six.moves import zip, zip_longest

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
from rest.helpers import identity, list_dict
from rest.hierarchy_traverser import all_paths, create_graph
from rest.introspect import pk_attr_name
from rest.query import query
from rest.schema import to_jsonschema
from sqlalchemy.orm.base import MANYTOMANY
from six import iteritems


EndpointParams = namedtuple('EndpointParams', 'rule endpoint view_func methods')


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
            for method, rh in iteritems(j)]


def schemas_for_paths(paths, config, graph):
    all_models = set(list(chain.from_iterable(paths)))
    schemas = {m: to_jsonschema(config[m]['schema']) for m in all_models}
    model_relation_pairs = chain.from_iterable([zip(p, p[1:]) for p in paths])
    by_model = list_dict(model_relation_pairs)
    root = paths[0][0]
    print(root)

    for m, s in iteritems(schemas):
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


def join_on(graph, child, parent):
    if parent and is_many_to_many(graph, child, parent):
        rel_attr = graph[parent][child]['rel_attr']
        return getattr(parent, rel_attr)
    else:
        return parent


def apis_for_path(path, config, db_session, graph):
    col_rule, item_rule = url_rules_for_path(path[1:], config, graph)
    model = path[-1]
    parent = path[-2]
    model_config = config[model]
    endpoints = defaultdict(dict)

    ps = [m for m in reversed(path) if m is not None]

    attrs_to_filter = tuple((getattr(m, config[m]['exposed_attr'])
                             for m in ps))

    join_attrs = [join_on(graph, ch, p) for ch, p in zip(ps, ps[1:])]
    collection_query = partial(
        query,
        model_to_query=model,
        join_attrs=join_attrs,
        attrs_to_filter=attrs_to_filter[1:]
    )
    item_query = partial(
        query,
        model_to_query=model,
        join_attrs=join_attrs,
        attrs_to_filter=attrs_to_filter,
    )
    endpoints['collection']['GET'] = (
        col_rule, get_handler(
            partial(
                get_collection,
                db_session,
                collection_query,
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
        item_query,
    )

    if parent:
        rel_attr = graph[parent][model]['rel_attr']
        child_query = partial(
            query,
            model_to_query=model,
            attrs_to_filter=attrs_to_filter[0:1],
        )
        parent_query = partial(
            query,
            model_to_query=parent,
            join_attrs=join_attrs[1:],
            attrs_to_filter=attrs_to_filter[1:]
        )
        if is_many_to_many(graph, model, parent):
            h = partial(
                post_item_many_to_many,
                db_session,
                child_query,
                parent_query,
                rel_attr,
            )
            del_h = partial(
                delete_many_to_many,
                db_session,
                child_query,
                parent_query,
                rel_attr
            )
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
                item_query,
                model_config['item_serializer']
            )
        )
    )
    endpoints['item']['PATCH'] = (
        item_rule, data_handler(
            partial(
                patch_item,
                db_session,
                collection_query,
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
    out_schemas = deepcopy(schemas)
    for schema in out_schemas.values():
        for l in schema['links']:
            l['schema_key'] = str(l['schema_key'])
    eps.append(
        EndpointParams(
            rule='/schemas',
            endpoint='schemas',
            view_func=partial(
                schemas_handler,
                {str(m): schema for m, schema in iteritems(out_schemas)}
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
    apis = [
        apis_for_path((None,) + path, config, db_session, graph)
        for path in all_ps
    ]
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
        model, create_schema, db_session
    )
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


def url_rules_for_path(path, config, graph):
    model = path[0]
    url_names = chain(
        (config[model]['url_name'],),
        (graph[m1][m2]['rel_attr'] for m1, m2 in zip(path[0:], path[1:]))
    )
    patterns = ['<{}level_{}_id>'.format(config[model]['exposed_attr_type'], i)
                for i, m in enumerate(path)]
    np = tuple(zip(url_names, patterns))
    item_url_rule = '/'.join(
        chain([''], chain.from_iterable(np))
    )
    collection_url_rule = '/'.join(
        chain([''], chain.from_iterable(np[:-1]), [np[-1][0]])
    )
    return collection_url_rule, item_url_rule
