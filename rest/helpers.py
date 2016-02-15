from functools import reduce
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
