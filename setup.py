from setuptools import setup


setup(
    name='flask_alchemy_rest',
    version='0.1',
    py_modules=('rest',),
    install_requires=(
        'flask',
        'sqlalchemy',
        'marshmallow',
        'marshmallow_sqlalchemy',
        'networkx',
        'split',
        'six',
        'more_functools',
    ),
    dependency_links=(
        'https://github.com/purpleP/more_functools/tarball/master#egg=more_functools-1.0',
    ),
)
