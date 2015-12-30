import json


def get_json(test_client, url, query_dict=None):
    return json.loads(test_client.get(url, query_string=query_dict).data)


def post_json(test_client, url, data):
    return test_client.post(url, data=json.dumps(data), content_type='application/json')


def put_json(test_client, url, data):
    return test_client.put(url, data=json.dumps(data), content_type='application/json')