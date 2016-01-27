from functools import reduce


def inits(_list):
    return [_list[:i] for i in xrange(len(_list) + 1)]


def tails(_list):
    return [_list[i:] for i in xrange(len(_list) + 1)]


def identity(x):
    return x


def compose(*functions):
    return reduce(lambda f, g: lambda x: f(*g(*x)), functions, identity)


def apply_(f, *args, **kwargs):
    return f(*args, **kwargs)
