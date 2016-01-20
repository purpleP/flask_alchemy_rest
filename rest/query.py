def query(db_session, path, keys):
    def filter_(query_, mk):
        me, key = mk
        model, exposed_attr = me
        return query_.filter(
                getattr(model, exposed_attr) == key)

    path_part = path[1:] if len(keys) < len(path) else path[:]

    return reduce(filter_, zip(path_part, keys), db_session.query(path[0][0]))

