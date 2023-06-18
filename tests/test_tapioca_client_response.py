import json

from aiotapioca.client import TapiocaClientExecutor


async def test_available_attributes(mocked, client):
    next_url = "http://api.example.org/next_batch"
    data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

    mocked.get(
        client.test().path,
        body=json.dumps(data),
        status=200,
        content_type="application/json",
    )
    response = await client.test().get()
    dir_response = dir(response)
    expected_methods = sorted(
        [
            "api_params",
            "path",
            "resource",
            "resource_name",
            "session",
            "response",
            "status",
            "url",
            "request_kwargs",
            "data",
        ]
    )
    assert len(dir_response) == len(expected_methods)
    for attr, expected in zip(dir_response, expected_methods):
        assert attr == expected


async def test_callable_executor_from_response(mocked, client):
    next_url = "http://api.example.org/next_batch"
    data = {"data": [{"key": "value"}], "paging": {"next": next_url}}
    mocked.get(
        client.test().path,
        body=json.dumps(data),
        status=200,
        content_type="application/json",
    )
    response = await client.test().get()
    assert type(response()) is TapiocaClientExecutor
