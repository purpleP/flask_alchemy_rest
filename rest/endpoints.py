from collections import namedtuple

from rest.query import urls_for_path, params_from_path

EndpointParameters = namedtuple('EndpointParameters', 'model methods query_params url url_model_attr')


def make_handlers(graph, path):
    collection_url, item_url = urls_for_path(path)
    query_params = params_from_path(graph, path)
    model_info = path[0]
    return EndpointParameters(
        model=model_info.model,
        methods=['POST', 'GET'],
        query_params=query_params,
        url=collection_url,
        url_model_attr=model_info.url_attr
    ),
