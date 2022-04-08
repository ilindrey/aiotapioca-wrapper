import json

import pytest
import pytest_asyncio
import pickle
import xmltodict
from collections import OrderedDict

from aiohttp.client_reqrep import ClientResponse
from yarl import URL

from aiotapioca.adapters import TapiocaAdapter
from aiotapioca.exceptions import ClientError, ServerError
from aiotapioca.serializers import SimpleSerializer
from aiotapioca.tapioca import TapiocaClient, TapiocaClientExecutor
from .callbacks import callback_201, callback_401
from .clients import (
    SimpleClient,
    XMLClient,
    TokenRefreshClient,
    TokenRefreshByDefaultClient,
    FailTokenRefreshClient,
    RetryRequestClient,
    NoneSemaphoreClient,
)


@pytest_asyncio.fixture
async def retry_request_client():
    async with RetryRequestClient() as c:
        yield c


@pytest_asyncio.fixture
async def xml_client():
    async with XMLClient() as c:
        yield c


@pytest_asyncio.fixture
async def token_refresh_by_default_client():
    async with TokenRefreshByDefaultClient(token="token") as c:
        yield c


@pytest.fixture()
def refresh_token_possible_false_values():
    yield False, None, 1, 0, "511", -22, 41, [], tuple(), {}, set(), [41], {
        "key": "value"
    }


def check_response(response, data, status=200, refresh_data=None):
    executor = response()
    assert type(response) == TapiocaClient
    assert type(executor) == TapiocaClientExecutor
    assert executor.data == data
    assert executor.refresh_data == refresh_data
    assert isinstance(executor.response, ClientResponse)
    assert executor.status == status


async def check_pages_responses(
    response, total_pages=1, max_pages=None, max_items=None
):
    result_response = {
        response: {
            "data": [{"key": "value"}],
            "paging": {"next": "http://api.example.org/next_batch"},
        },
        response.data: [{"key": "value"}],
        response.paging: {"next": "http://api.example.org/next_batch"},
        response.paging.next: "http://api.example.org/next_batch",
    }
    for resp, data in result_response.items():
        check_response(resp, data)

    iterations_count = 0
    async for item in response().pages(max_pages=max_pages, max_items=max_items):
        result_page = {item: {"key": "value"}, item.key: "value"}
        for resp, data in result_page.items():
            check_response(resp, data)
        iterations_count += 1
    assert iterations_count == total_pages


"""
test TapiocaClient
"""


def test_adapter_class_default_attributes():

    assert isinstance(TapiocaAdapter.refresh_token, bool)
    assert isinstance(TapiocaAdapter.semaphore, int)
    assert isinstance(TapiocaAdapter.serializer_class, object)

    assert TapiocaAdapter.refresh_token is False
    assert TapiocaAdapter.semaphore == 10
    assert TapiocaAdapter.serializer_class == SimpleSerializer


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


async def test_requests(mocked, client):

    semaphores = (3, None)
    types_request = ("get", "post", "put", "patch", "delete")
    for semaphore, type_request in zip(semaphores, types_request):

        executor = client.test()

        status = 200 if type_request == "get" else 201

        mocked_method = getattr(mocked, type_request)
        executor_method = getattr(executor, type_request)

        mocked_method(
            executor.data,
            body='{"data": {"key": "value"}}',
            status=status,
            content_type="application/json",
        )

        kwargs = {}
        if semaphore:
            kwargs.update({"semaphore": semaphore})

        response = await executor_method(**kwargs)

        result_response = {
            response: {"data": {"key": "value"}},
            response.data: {"key": "value"},
            response.data.key: "value",
        }

        for response, data in result_response.items():
            check_response(response, data, status)


async def test_batch_requests(mocked, client):
    response_data = [
        {"data": {"key": "value"}},
        {"data": {"key": "value"}},
        {"data": {"key": "value"}},
    ]
    semaphores = (3, None)
    types_request = ("post", "put", "patch", "delete")
    for semaphore, type_request in zip(semaphores, types_request):

        executor = client.test()
        mocked_method = getattr(mocked, type_request)
        executor_method = getattr(executor, type_request + "_batch")

        for data_row in response_data:
            mocked_method(
                executor.data,
                body=json.dumps(data_row),
                status=201,
                content_type="application/json",
            )

        kwargs = dict(data=response_data)
        if semaphore:
            kwargs.update({"semaphore": semaphore})

        results = await executor_method(**kwargs)

        for i, response in enumerate(results):
            result_response = {
                response: response_data[i],
                response.data: response_data[i]["data"],
                response.data.key: response_data[i]["data"]["key"],
            }
            for resp, data in result_response.items():
                check_response(resp, data, 201)

        assert len(results) == len(response_data)


async def test_as_api_params_requests(mocked):

    debug_flags = (True, False)
    semaphores = (4, None, False)
    types_request = ("get", "post", "put", "patch", "delete")

    for debug, semaphore, type_request in zip(debug_flags, semaphores, types_request):

        async with SimpleClient(semaphore=semaphore, debug=True) as simple_client:

            executor = simple_client.test()

            status = 200 if type_request == "get" else 201

            mocked_method = getattr(mocked, type_request)
            executor_method = getattr(executor, type_request)

            mocked_method(
                executor.data,
                body='{"data": {"key": "value"}}',
                status=status,
                content_type="application/json",
            )

            kwargs = dict()

            response = await executor_method(**kwargs)

            result_response = {
                response: {"data": {"key": "value"}},
                response.data: {"key": "value"},
                response.data.key: "value",
            }

            for response, data in result_response.items():
                check_response(response, data, status)
                assert response()._api_params.get("semaphore") == semaphore


async def test_as_api_params_batch_requests(mocked):
    response_data = [
        {"data": {"key": "value"}},
        {"data": {"key": "value"}},
        {"data": {"key": "value"}},
    ]

    debug_flags = (True, False)
    semaphores = (4, None, False)
    types_request = ("post", "put", "patch", "delete")

    for debug, semaphore, type_request in zip(debug_flags, semaphores, types_request):

        async with SimpleClient(semaphore=semaphore, debug=debug) as simple_client:

            executor = simple_client.test()
            mocked_method = getattr(mocked, type_request)
            executor_method = getattr(executor, type_request + "_batch")

            for data_row in response_data:
                mocked_method(
                    executor.data,
                    body=json.dumps(data_row),
                    status=201,
                    content_type="application/json",
                )

            kwargs = dict(data=response_data)
            if semaphore:
                kwargs.update({"semaphore": semaphore})

            results = await executor_method(**kwargs)

            for i, response in enumerate(results):
                result_response = {
                    response: response_data[i],
                    response.data: response_data[i]["data"],
                    response.data.key: response_data[i]["data"]["key"],
                }
                for resp, data in result_response.items():
                    check_response(resp, data, 201)
                    assert resp()._api_params.get("semaphore") == semaphore

            assert len(results) == len(response_data)


async def test_failed_semaphore(mocked):

    async with NoneSemaphoreClient() as none_semaphore_client:
        mocked.get(
            none_semaphore_client.test().data,
            body='{"data": {"key": "value"}}',
            status=200,
            content_type="application/json",
        )

        with pytest.raises(TypeError):
            await none_semaphore_client.test().get()


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

    await check_pages_responses(response, total_pages=2)


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

    await check_pages_responses(response, total_pages=7, max_pages=3)


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

    await check_pages_responses(response, total_pages=3, max_items=3)


async def test_simple_pages_with_max_pages_and_max_items_iterator(mocked, client):
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

    await check_pages_responses(response, total_pages=3, max_pages=2, max_items=3)


async def test_simple_pages_max_pages_zero_iterator(mocked, client):
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

    await check_pages_responses(response, total_pages=0, max_pages=0)


async def test_simple_pages_max_items_zero_iterator(mocked, client):
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

    await check_pages_responses(response, total_pages=0, max_items=0)


async def test_simple_pages_max_pages_ans_max_items_zero_iterator(mocked, client):
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

    await check_pages_responses(response, total_pages=0, max_pages=0, max_items=0)


async def test_pages_iterator_with_client_error(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=408,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()
    result_response = {
        response: {
            "data": [{"key": "value"}],
            "paging": {"next": "http://api.example.org/next_batch"},
        },
        response.data: [{"key": "value"}],
        response.paging: {"next": "http://api.example.org/next_batch"},
        response.paging.next: "http://api.example.org/next_batch",
    }
    for resp, data in result_response.items():
        check_response(resp, data)

    iterations_count = 0
    with pytest.raises(ClientError):
        async for item in response().pages():
            result_page = {item: {"key": "value"}, item.key: "value"}
            for resp, data in result_page.items():
                check_response(resp, data)
            iterations_count += 1
    assert iterations_count == 2


async def test_pages_iterator_with_server_error(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=504,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()
    result_response = {
        response: {
            "data": [{"key": "value"}],
            "paging": {"next": "http://api.example.org/next_batch"},
        },
        response.data: [{"key": "value"}],
        response.paging: {"next": "http://api.example.org/next_batch"},
        response.paging.next: "http://api.example.org/next_batch",
    }
    for resp, data in result_response.items():
        check_response(resp, data)

    iterations_count = 0
    with pytest.raises(ServerError):
        async for item in response().pages():
            result_page = {item: {"key": "value"}, item.key: "value"}
            for resp, data in result_page.items():
                check_response(resp, data)
            iterations_count += 1
    assert iterations_count == 2


async def test_pages_iterator_with_error_on_single_page(mocked, client):
    next_url = "http://api.example.org/next_batch"

    mocked.get(
        client.test().data,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": "%s"}}' % next_url,
        status=200,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{}], "paging": {"next": "%s"}}' % next_url,
        status=204,
        content_type="application/json",
    )

    mocked.get(
        next_url,
        body='{"data": [{"key": "value"}], "paging": {"next": ""}}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()
    result_response = {
        response: {
            "data": [{"key": "value"}],
            "paging": {"next": "http://api.example.org/next_batch"},
        },
        response.data: [{"key": "value"}],
        response.paging: {"next": "http://api.example.org/next_batch"},
        response.paging.next: "http://api.example.org/next_batch",
    }
    for resp, data in result_response.items():
        check_response(resp, data)

    iterations_count = 0
    async for item in response().pages():
        if iterations_count == 2:
            status = 204
            result_page = {item: dict()}
        else:
            status = 200
            result_page = {item: {"key": "value"}, item.key: "value"}
        for resp, data in result_page.items():
            check_response(resp, data, status)
        iterations_count += 1
    assert iterations_count == 4


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


async def test_disable_token_refreshing(mocked, refresh_token_possible_false_values):

    async with TokenRefreshClient(token="token") as token_refreshing_client:
        mocked.post(
            token_refreshing_client.test().data,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await token_refreshing_client.test().post()

    for refresh_token in refresh_token_possible_false_values:
        async with TokenRefreshClient(
            token="token", refresh_token=refresh_token
        ) as token_refreshing_client:
            mocked.post(
                token_refreshing_client.test().data,
                callback=callback_401,
                content_type="application/json",
            )

            with pytest.raises(ClientError):
                await token_refreshing_client.test().post()

        async with TokenRefreshClient(token="token") as token_refreshing_client:
            mocked.post(
                token_refreshing_client.test().data,
                callback=callback_401,
                content_type="application/json",
            )

            with pytest.raises(ClientError):
                await token_refreshing_client.test().post(refresh_token=refresh_token)


async def test_token_expired_automatically_refresh_authentication(mocked):

    async with TokenRefreshClient(token="token") as token_refresh_client:

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

        response = await token_refresh_client.test().post(refresh_token=True)

        # refresh_authentication method should be able to update api_params
        assert response._api_params["token"] == "new_token"

        mocked.post(
            token_refresh_client.test().data,
            callback=callback_401,
            content_type="application/json",
        )
        mocked.post(
            token_refresh_client.test().data,
            callback=callback_401,
            content_type="application/json",
        )

        # check that the refresh_token flag is not cyclic
        with pytest.raises(ClientError):
            await token_refresh_client.test().post(refresh_token=True)

    async with TokenRefreshClient(
        token="token", refresh_token=True
    ) as token_refresh_client:
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

        mocked.post(
            token_refresh_client.test().data,
            callback=callback_401,
            content_type="application/json",
        )
        mocked.post(
            token_refresh_client.test().data,
            callback=callback_401,
            content_type="application/json",
        )

        # check that the refresh_token flag is not cyclic
        with pytest.raises(ClientError):
            await token_refresh_client.test().post()


async def test_token_expired_automatically_refresh_authentication_by_default(
    mocked, token_refresh_by_default_client
):

    mocked.post(
        token_refresh_by_default_client.test().data,
        callback=callback_401,
        content_type="application/json",
    )

    mocked.post(
        token_refresh_by_default_client.test().data,
        callback=callback_201,
        content_type="application/json",
    )

    response = await token_refresh_by_default_client.test().post()

    # refresh_authentication method should be able to update api_params
    assert response._api_params["token"] == "new_token"

    mocked.post(
        token_refresh_by_default_client.test().data,
        callback=callback_401,
        content_type="application/json",
    )
    mocked.post(
        token_refresh_by_default_client.test().data,
        callback=callback_401,
        content_type="application/json",
    )

    # check that the refresh_token flag is not cyclic
    with pytest.raises(ClientError):
        await token_refresh_by_default_client.test().post()


async def test_raises_error_if_refresh_authentication_method_returns_false_value(
    mocked, refresh_token_possible_false_values
):
    async with FailTokenRefreshClient(token="token") as fail_client:

        mocked.post(
            fail_client.test().data,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await fail_client.test().post()

    for refresh_token in (True, *refresh_token_possible_false_values):

        async with FailTokenRefreshClient(
            token="token", refresh_token=refresh_token
        ) as fail_client:

            mocked.post(
                fail_client.test().data,
                callback=callback_401,
                content_type="application/json",
            )

            with pytest.raises(ClientError):
                await fail_client.test().post()

        async with FailTokenRefreshClient(token="token") as fail_client:

            mocked.post(
                fail_client.test().data,
                callback=callback_401,
                content_type="application/json",
            )

            with pytest.raises(ClientError):
                await fail_client.test().post(refresh_token=refresh_token)
