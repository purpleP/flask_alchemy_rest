# flask_alchemy_rest

This library provides a way to create REST API from existing sqlalchemy models.

```python
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core_api.models import Material, Slice, Base
from rest.endpoints import create_api, register_all_apis


engine = create_engine('sqlite:////tmp/test.db')
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()
app = Flask(__name__)


apis, schema = create_api(
    Material, session
)
register_all_apis(app, schema, (apis,))
app.run(host='0.0.0.0', port=5000)
```

There a similar libraries and frameworks for that. This one has important differences from them.

1. It can handle many-to-many relationships. Like Company has many employees and employe can work in multiple companies.
2. It can handle relationships of unlimited deepness.
3. You can use existing sqlalchemy models.

1. [Flask-restless](https://flask-restless.readthedocs.io/en/stable/). Trying to do the same basically, but can't handle relationships deeper than 1 level.

2. [Sandman] (https://github.com/jeffknupp/sandman). I've only briefly tried, but the main point is that it can only create api from models created by reflection abilities of sqlalchemy.
