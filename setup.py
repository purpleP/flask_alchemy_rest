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
    )
)
