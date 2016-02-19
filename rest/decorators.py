from functools import partial, reduce
from collections import defaultdict


from rest.handlers import (
    create_schema,
    deserialize_item,
    serialize_collection,
    serialize_item,
)
from sqlalchemy.orm.base import MANYTOMANY, ONETOMANY, MANYTOONE


def without_relations(session, graph, config):
    for m, conf in config.iteritems():

        def by_rel_type(acc, relation):
            rel_info = graph[m][relation]
            if rel_info['rel_type'] in (MANYTOMANY, ONETOMANY):
                acc['exclude'] += rel_info['rel_attr'],
            elif rel_info['rel_type'] == MANYTOONE:
                acc['dump_only'] += rel_info['rel_attr'],
            return acc
        acc = defaultdict(tuple)
        schema_attrs = reduce(by_rel_type, graph.successors(m), acc)
        schema = create_schema(m, schema_attrs)()
        conf['collection_serializer'] = partial(
            serialize_collection,
            schema,
        )
        conf['item_serializer'] = partial(
            serialize_item,
            schema,
        )
        conf['item_deserializer'] = partial(
            deserialize_item,
            schema,
            session,
        )
    return config
