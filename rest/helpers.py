from functools import reduce
from collections import Mapping, defaultdict
from operator import concat


def inits(_list):
    return [_list[:i] for i in xrange(len(_list) + 1)]


def tails(_list):
    return [_list[i:] for i in xrange(len(_list) + 1)]


def identity(x):
    return x


def wrapper_id(*args, **kwargs):
    return args, kwargs


def compose(*wrappers):
    def l(f, g):
        def l2(*args, **kwargs):
            a, kw = g(*args, **kwargs)
            return f(*a, **kw)
        return l2

    return reduce(l, wrappers, wrapper_id)


def concat_(seqs):
    return reduce(concat, seqs, ())


def apply_(f, *args, **kwargs):
    return f(*args, **kwargs)


def find(predicate, iterable):
    return next((x for x in iterable if predicate(x)), None)


def list_dict(pairs):
    def to_dict(acc, v):
        acc[v[0]].append(v[1])
        return acc
    return reduce(to_dict, pairs, defaultdict(list))


def merge(d1, d2, path=[]):
    for k, d2v in d2.iteritems():
        if k in d1:
            d1v = d1[k]
            if isinstance(d1v, Mapping) and isinstance(d2v, Mapping):
                merge(d1v, d2v, path + [str(k)])
            elif isinstance(d1v, list) and isinstance(d2v, list):
                unique_links_as_tuples = set(
                    [tuple(ld.items()) for ld in d1v + d2v]
                )
                d1[k] = [dict(t) for t in unique_links_as_tuples]
            elif d1v == d2v:
                pass
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(k)]))
        else:
            d1[k] = d2v
    return d1
