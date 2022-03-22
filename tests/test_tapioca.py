import json

import pytest
import pickle
import xmltodict
from collections import OrderedDict
from yarl import URL

from aiotapioca.tapioca import TapiocaClient
from aiotapioca.exceptions import ClientError, ServerError
from .clients import SimpleClient, FailTokenRefreshClient
from .callbacks import callback_201, callback_401
from .fixtures import (
    mocked,
    client,
    token_refresh_client,
    xml_client,
    token_refresh_client,
    retry_request_client,
)


"""
test TapiocaClient
"""


def test_fill_url_template(client):
    expected_url = "https://api.example.org/user/123/"
    resource = client.user(id="123")
    assert resource.data == expected_url


def test_fill_another_root_url_template(client):
    expected_url = "https://api.another.com/another-root/"
    resource = client.another_root()
    assert resource.data == expected_url


def test_calling_len_on_tapioca_list(client):
    wrap_client = client._wrap_in_tapioca([0, 1, 2])
    assert len(wrap_client) == 3


def test_iterated_client_items_should_be_tapioca_instances(client):
    wrap_client = client._wrap_in_tapioca([0, 1, 2])

    for item in wrap_client:
        assert isinstance(item, TapiocaClient)


def test_iterated_client_items_should_contain_list_items(client):
    wrap_client = client._wrap_in_tapioca([0, 1, 2])

    for i, item in enumerate(wrap_client):
        assert item().data == i


async def test_in_operator(mocked, client):
    mocked.get(
        client.test().data,
        body='{"data": 1, "other": 2}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    assert "data" in response
    assert "other" in response
    assert "wat" not in response


async def test_transform_camelCase_in_snake_case(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.add(
        client.test().data,
        body='{"data" :{"key_snake": "value", "camelCase": "data in camel case", "NormalCamelCase": "data in camel case"}, "paging": {"next": "%s"}}'
        % next_url,
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    assert response.data.key_snake().data == "value"
    assert response.data.camel_case().data == "data in camel case"
    assert response.data.normal_camel_case().data == "data in camel case"


async def test_should_be_able_to_access_by_index(mocked, client):
    mocked.get(
        client.test().data,
        body='["a", "b", "c"]',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    assert response[0]().data == "a"
    assert response[1]().data == "b"
    assert response[2]().data == "c"


async def test_accessing_index_out_of_bounds_should_raise_index_error(mocked, client):
    mocked.get(
        client.test().data,
        body='["a", "b", "c"]',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    with pytest.raises(IndexError):
        response[3]


async def test_accessing_empty_list_should_raise_index_error(mocked, client):
    mocked.get(
        client.test().data, body="[]", status=200, content_type="application/json"
    )

    response = await client.test().get()

    with pytest.raises(IndexError):
        response[3]


def test_fill_url_from_default_params():
    client = SimpleClient(default_url_params={"id": 123})
    assert client.user().data == "https://api.example.org/user/123/"


async def test_is_pickleable(mocked):
    pickle_client = pickle.loads(pickle.dumps(SimpleClient()))

    # ensure requests keep working after pickle:
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        pickle_client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    async with pickle_client:
        response = await pickle_client.test().get()

        iterations_count = 0
        async for item in response().pages():
            assert "value" in item.key().data
            iterations_count += 1
        assert iterations_count == 2


"""
test TapiocaExecutor
"""


def test_resource_executor_data_should_be_composed_url(client):
    expected_url = "https://api.example.org/test/"
    resource = client.test()
    assert resource.data == expected_url


def test_docs(client):
    assert "\n".join(client.resource.__doc__.split("\n")[1:]) == (
        "Resource: " + client.resource._resource["resource"] + "\n"
        "Docs: " + client.resource._resource["docs"] + "\n"
        "Foo: " + client.resource._resource["foo"] + "\n"
        "Spam: " + client.resource._resource["spam"]
    )


def test_access_data_attributres_through_executor(client):
    wrap_client = client._wrap_in_tapioca({"test": "value"})

    items = wrap_client().items()

    assert isinstance(items, TapiocaClient)

    data = dict(items().data)

    assert data == {"test": "value"}


def test_is_possible_to_reverse_a_list_through_executor(client):
    wrap_client = client._wrap_in_tapioca([0, 1, 2])
    wrap_client().reverse()
    assert wrap_client().data == [2, 1, 0]


def test_cannot__getittem__(client):
    wrap_client = client._wrap_in_tapioca([0, 1, 2])
    with pytest.raises(Exception):
        wrap_client()[0]


def test_cannot_iterate(client):
    wrap_client = client._wrap_in_tapioca([0, 1, 2])
    with pytest.raises(Exception):
        for item in wrap_client():
            pass


def test_dir_call_returns_executor_methods(client):
    wrap_client = client._wrap_in_tapioca([0, 1, 2])

    e_dir = dir(wrap_client())

    assert "data" in e_dir
    assert "response" in e_dir
    assert "get" in e_dir
    assert "post" in e_dir
    assert "post_batch" in e_dir
    assert "pages" in e_dir
    assert "open_docs" in e_dir
    assert "open_in_browser" in e_dir


async def test_response_executor_object_has_a_response(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    executor = response()

    assert executor.response is not None
    assert executor._response is not None
    assert executor.response.status == 200
    assert executor._response.status == 200


def test_raises_error_if_executor_does_not_have_a_response_object(client):
    with pytest.raises(Exception):
        client().response


async def test_response_executor_has_a_status_code(mocked, client):
    mocked.get(
        client.test().data,
        body='{"data": {"key": "value"}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    assert response().status == 200


"""
test TapiocaExecutor requests
"""


def test_when_executor_has_no_response(client):
    with pytest.raises(Exception) as context:
        client.test().response

        exception = context.exception

        assert "has no response" == str(exception)


async def test_access_response_field(mocked, client):
    mocked.get(
        client.test().data,
        body='{"data": {"key": "value"}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    response_data = response.data()

    assert response_data.data == {"key": "value"}


async def test_get_request(mocked, client):
    for debug in (True, False):
        mocked.get(
            client.test().data,
            body='{"data": {"key": "value"}}',
            status=200,
            content_type="application/json",
        )

        response = await client.test().get(debug=debug)

        assert response().data == {"data": {"key": "value"}}


async def test_post_request(mocked, client):
    for debug in (True, False):
        mocked.post(
            client.test().data,
            body='{"data": {"key": "value"}}',
            status=201,
            content_type="application/json",
        )

        response = await client.test().post(debug=debug)

        assert response().data == {"data": {"key": "value"}}


async def test_put_request(mocked, client):
    for debug in (True, False):
        mocked.put(
            client.test().data,
            body='{"data": {"key": "value"}}',
            status=201,
            content_type="application/json",
        )

        response = await client.test().put(debug=debug)

        assert response().data == {"data": {"key": "value"}}


async def test_patch_request(mocked, client):
    for debug in (True, False):
        mocked.patch(
            client.test().data,
            body='{"data": {"key": "value"}}',
            status=201,
            content_type="application/json",
        )

        response = await client.test().patch(debug=debug)

        assert response().data == {"data": {"key": "value"}}


async def test_delete_request(mocked, client):
    for debug in (True, False):
        mocked.delete(
            client.test().data,
            body='{"data": {"key": "value"}}',
            status=201,
            content_type="application/json",
        )

        response = await client.test().delete(debug=debug)

        assert response().data, {"data": {"key": "value"}}


async def test_post_batch(mocked, client):
    for debug in (True, False):
        data = [
            {"data": [{"key": "value"}]},
            {"data": [{"key": "value"}]},
            {"data": [{"key": "value"}]},
        ]

        for row in data:
            mocked.post(
                client.test().data,
                body=json.dumps(row),
                status=200,
                content_type="application/json",
            )

        results = await client.test().post_batch(data=data, debug=debug)

        for response, data_row in zip(results, data):
            assert response().data == data_row

        assert len(results) == len(data)


async def test_put_batch(mocked, client):
    for debug in (True, False):
        data = [
            {"data": [{"key": "value"}]},
            {"data": [{"key": "value"}]},
            {"data": [{"key": "value"}]},
        ]

        for row in data:
            mocked.put(
                client.test().data,
                body=json.dumps(row),
                status=200,
                content_type="application/json",
            )

        results = await client.test().put_batch(data=data, debug=debug)

        for response, data_row in zip(results, data):
            assert response().data == data_row

        assert len(results) == len(data)


async def test_patch_batch(mocked, client):
    for debug in (True, False):
        data = [
            {"data": [{"key": "value"}]},
            {"data": [{"key": "value"}]},
            {"data": [{"key": "value"}]},
        ]

        for row in data:
            mocked.patch(
                client.test().data,
                body=json.dumps(row),
                status=200,
                content_type="application/json",
            )

        results = await client.test().patch_batch(data=data, debug=debug)

        for response, data_row in zip(results, data):
            assert response().data == data_row

        assert len(results) == len(data)


async def test_delete_batch(mocked, client):
    for debug in (True, False):
        data = [
            {"data": [{"key": "value"}]},
            {"data": [{"key": "value"}]},
            {"data": [{"key": "value"}]},
        ]

        for row in data:
            mocked.delete(
                client.test().data,
                body=json.dumps(row),
                status=200,
                content_type="application/json",
            )

        results = await client.test().delete_batch(data=data, debug=debug)

        for response, data_row in zip(results, data):
            assert response().data == data_row

        assert len(results) == len(data)


async def test_carries_request_kwargs_over_calls(mocked, client):
    mocked.get(
        client.test().data,
        body='{"data": {"key": "value"}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    request_kwargs = response.data.key()._request_kwargs

    assert "url" in request_kwargs
    assert "data" in request_kwargs
    assert "headers" in request_kwargs


async def test_thrown_tapioca_exception_with_client_error_data(mocked, client):
    mocked.get(
        client.test().data,
        body='{"error": "bad request test"}',
        status=400,
        content_type="application/json",
    )
    with pytest.raises(ClientError) as client_exception:
        await client.test().get()
    assert "bad request test" in client_exception.value.args


async def test_thrown_tapioca_exception_with_server_error_data(mocked, client):
    mocked.get(
        client.test().data,
        body='{"error": "server error test"}',
        status=500,
        content_type="application/json",
    )
    with pytest.raises(ServerError) as server_exception:
        await client.test().get()
    assert "server error test" in server_exception.value.args


async def test_retry_request(mocked, retry_request_client):
    for _ in range(10):
        mocked.get(
            retry_request_client.test().data,
            body='{"error": "bad request test"}',
            status=400,
            content_type="application/json",
        )

    mocked.get(
        retry_request_client.test().data,
        body='{"data": "success!"}',
        status=200,
        content_type="application/json",
    )

    response = await retry_request_client.test().get()

    assert response.data().data == "success!"

    for _ in range(3):
        mocked.get(
            retry_request_client.test().data,
            body='{"error": "bad request test"}',
            status=400,
            content_type="application/json",
        )

    mocked.get(
        retry_request_client.test().data,
        body='{"data": "success!"}',
        status=200,
        content_type="application/json",
    )

    response = await retry_request_client.test().get()

    assert response.data().data == "success!"

    for _ in range(3):
        mocked.get(
            retry_request_client.test().data,
            body='{"error": "bad request test"}',
            status=403,
            content_type="application/json",
        )

    with pytest.raises(ClientError):
        await retry_request_client.test().get()


"""
test iterator features
"""


async def test_simple_pages_iterator(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    iterations_count = 0
    async for item in response().pages():
        assert "value" in item.key().data
        iterations_count += 1
    assert iterations_count == 2


async def test_simple_pages_with_max_items_iterator(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}, {"key": "value"}, {"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    iterations_count = 0
    async for item in response().pages(max_items=3, max_pages=2):
        assert "value" in item.key().data
        iterations_count += 1
    assert iterations_count == 3


async def test_simple_pages_with_max_pages_iterator(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )
    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}, {"key": "value"}, {"key": "value"}], "paging": {"next": "%s"}}'
        % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}, {"key": "value"}, {"key": "value"}], "paging": {"next": "%s"}}'
        % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}, {"key": "value"}, {"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    iterations_count = 0
    async for item in response().pages(max_pages=3):
        assert "value" in item.key().data
        iterations_count += 1
    assert iterations_count == 7


async def test_simple_pages_max_page_zero_iterator(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.add(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    iterations_count = 0
    async for item in response().pages(max_pages=0):
        assert "value" in item.key().data
        iterations_count += 1
    assert iterations_count == 0


async def test_simple_pages_max_item_zero_iterator(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    iterations_count = 0
    async for item in response().pages(max_items=0):
        assert "value" in item.key().data
        iterations_count += 1
    assert iterations_count == 0


"""
test token refreshing
"""


async def test_not_token_refresh_client_propagates_client_error(mocked, client):
    no_refresh_client = client

    mocked.post(
        no_refresh_client.test().data,
        callback=callback_401,
        content_type="application/json",
    )

    with pytest.raises(ClientError):
        await no_refresh_client.test().post()


async def test_disable_token_refreshing(mocked, token_refresh_client):
    mocked.post(
        token_refresh_client.test().data,
        callback=callback_401,
        content_type="application/json",
    )

    with pytest.raises(ClientError):
        await token_refresh_client.test().post(refresh_token=False)


async def test_token_expired_automatically_refresh_authentication(
    mocked, token_refresh_client
):
    mocked.post(
        token_refresh_client.test().data,
        callback=callback_401,
        content_type="application/json",
    )

    mocked.post(
        token_refresh_client.test().data,
        callback=callback_201,
        content_type="application/json",
    )

    response = await token_refresh_client.test().post()

    # refresh_authentication method should be able to update api_params
    assert response._api_params["token"] == "new_token"


async def test_stores_refresh_authentication_method_response_for_further_access(
    mocked, token_refresh_client
):
    mocked.post(
        token_refresh_client.test().data,
        callback=callback_401,
        content_type="application/json",
    )

    mocked.post(
        token_refresh_client.test().data,
        callback=callback_201,
        content_type="application/json",
    )

    response = await token_refresh_client.test().post()

    # refresh_authentication method should be able to update api_params
    assert response().refresh_data == "new_token"


async def test_raises_error_if_refresh_authentication_method_returns_falsy_value(
    mocked,
):
    async with FailTokenRefreshClient(
        token="token", refresh_token_by_default=True
    ) as fail_client:

        mocked.post(
            fail_client.test().data,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await fail_client.test().post()


"""
test XML requests
"""


async def test_xml_post_string(mocked, xml_client):
    mocked.post(
        xml_client.test().data,
        body="Any response",
        status=200,
        content_type="application/json",
    )

    data = '<tag1 attr1="val1">' "<tag2>text1</tag2>" "<tag3>text2</tag3>" "</tag1>"

    await xml_client.test().post(data=data)

    request_body = mocked.requests[("POST", URL(xml_client.test().data))][0].kwargs[
        "data"
    ]

    assert request_body == data.encode("utf-8")


async def test_xml_post_dict(mocked, xml_client):
    mocked.post(
        xml_client.test().data,
        body="Any response",
        status=200,
        content_type="application/json",
    )

    data = OrderedDict(
        [
            (
                "tag1",
                OrderedDict([("@attr1", "val1"), ("tag2", "text1"), ("tag3", "text2")]),
            )
        ]
    )

    await xml_client.test().post(data=data)

    request_body = mocked.requests[("POST", URL(xml_client.test().data))][0].kwargs[
        "data"
    ]

    assert request_body == xmltodict.unparse(data).encode("utf-8")


async def test_xml_post_dict_passes_unparse_param(mocked, xml_client):
    mocked.post(
        xml_client.test().data,
        body="Any response",
        status=200,
        content_type="application/json",
    )

    data = OrderedDict(
        [
            (
                "tag1",
                OrderedDict([("@attr1", "val1"), ("tag2", "text1"), ("tag3", "text2")]),
            )
        ]
    )

    await xml_client.test().post(data=data, xmltodict_unparse__full_document=False)

    request_body = mocked.requests[("POST", URL(xml_client.test().data))][0].kwargs[
        "data"
    ]

    assert request_body == xmltodict.unparse(data, full_document=False).encode("utf-8")


async def test_xml_returns_text_if_response_not_xml(mocked, xml_client):
    mocked.post(
        xml_client.test().data,
        body="Any response",
        status=200,
        content_type="any content",
    )

    data = OrderedDict(
        [
            (
                "tag1",
                OrderedDict([("@attr1", "val1"), ("tag2", "text1"), ("tag3", "text2")]),
            )
        ]
    )

    response = await xml_client.test().post(data=data)

    assert "Any response" == response().data["text"]


async def test_xml_post_dict_returns_dict_if_response_xml(mocked, xml_client):
    xml_body = '<tag1 attr1="val1">text1</tag1>'
    mocked.post(
        xml_client.test().data,
        body=xml_body,
        status=200,
        content_type="application/xml",
    )

    data = OrderedDict(
        [
            (
                "tag1",
                OrderedDict([("@attr1", "val1"), ("tag2", "text1"), ("tag3", "text2")]),
            )
        ]
    )

    response = await xml_client.test().post(data=data)

    assert response().data == xmltodict.parse(xml_body)
