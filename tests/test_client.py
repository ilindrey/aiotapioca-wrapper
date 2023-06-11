import json
import pickle
from itertools import product

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from aiotapioca.client import ProcessData, TapiocaClientExecutor, TapiocaClientResponse
from aiotapioca.exceptions import ClientError, ServerError

from .callbacks import callback_201, callback_401
from .clients import (
    ClassMethodParserClient,
    ClassParserClient,
    DictParserClient,
    FailTokenRefreshClient,
    FuncParserClient,
    RetryRequestClient,
    SimpleClient,
    StaticMethodParserClient,
    TokenRefreshByDefaultClient,
    TokenRefreshClient,
)


def check_response(current_data, expected_data, response, status=200):
    assert type(current_data) is ProcessData
    assert type(response) is TapiocaClientResponse
    assert current_data() == expected_data
    assert response.status == status


async def check_pages_responses(
    response, total_pages=1, max_pages=None, max_items=None
):
    result_response = {
        response.data: {
            "data": [{"key": "value"}],
            "paging": {"next": "http://api.example.org/next_batch"},
        },
        response.data.data: [{"key": "value"}],
        response.data.paging: {"next": "http://api.example.org/next_batch"},
        response.data.paging.next: "http://api.example.org/next_batch",
    }
    for current_data, expected_data in result_response.items():
        check_response(current_data, expected_data, response)

    iterations_count = 0
    async for page in response().pages(max_pages=max_pages, max_items=max_items):
        result_page = {page.data: {"key": "value"}, page.data.key: "value"}
        for current_data, expected_data in result_page.items():
            check_response(current_data, expected_data, page)
        iterations_count += 1
    assert iterations_count == total_pages


class TestTapiocaClient:
    def test_available_attributes(self, client):
        dir_var = dir(client)
        resources = client._api.get_resource_mapping(client._api_params)
        expected_methods = sorted(
            [*resources, "api_params", "close", "closed", "initialize", "session"]
        )
        assert len(dir_var) == len(expected_methods)
        for attr, expected in zip(dir_var, expected_methods):
            assert attr == expected

    async def test_await_initialize(self):
        client = await SimpleClient()
        assert isinstance(client.session, ClientSession) and not client.session.closed
        assert not client.closed

    async def test_close_session(self):
        client = await SimpleClient()

        assert not client.closed

        await client.close()

        assert client.closed
        assert client.session is None

    async def test_initialize_with_context_manager(self):
        client = SimpleClient()
        await client.__aenter__()

        assert isinstance(client.session, ClientSession) and not client.session.closed
        assert not client.closed

        await client.__aexit__(None, None, None)

        assert client.closed
        assert client.session is None

    async def test_is_pickleable(self, mocked):
        pickle_client = pickle.loads(pickle.dumps(SimpleClient()))

        # ensure requests keep working after pickle:
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}
        mocked.get(
            pickle_client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["paging"]["next"] = ""
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        async with pickle_client:
            response = await pickle_client.test().get()

            iterations_count = 0
            async for page in response().pages():
                assert page.data.key() == "value"
                iterations_count += 1
            assert iterations_count == 2


class TestTapiocaClientResource:
    def test_available_attributes(self, client):
        dir_var = dir(client.test)
        expected_methods = sorted(
            [
                "api_params",
                "open_docs",
                "path",
                "resource",
                "resource_name",
                "session",
                "test",
            ]
        )
        assert len(dir_var) == len(expected_methods)
        for attr, expected in zip(dir_var, expected_methods):
            assert attr == expected

    def test_fill_url_template(self, client):
        expected_url = "https://api.example.org/user/123/"
        executor = client.user(id="123")
        assert executor.path == expected_url

    def test_fill_url_from_default_params(self):
        client = SimpleClient(default_url_params={"id": 123})
        assert client.user().path == "https://api.example.org/user/123/"

    def test_fill_another_root_url_template(self, client):
        expected_url = "https://api.another.com/another-root/"
        resource = client.another_root()
        assert resource.path == expected_url

    def test_contains(self, client):
        assert "resource" in client.resource
        assert "docs" in client.resource
        assert "foo" in client.resource
        assert "spam" in client.resource

    def test_docs(self, client):
        expected = (
            f"Resource: {client.resource.resource['resource']}\n"
            f"Docs: {client.resource.resource['docs']}\n"
            f"Foo: {client.resource.resource['foo']}\n"
            f"Spam: {client.resource.resource['spam']}"
        )
        assert "\n".join(client.resource.__doc__.split("\n")[1:]) == expected


class TestTapiocaClientExecutor:
    def test_available_attributes(self, client):
        dir_var = dir(client.test())
        expected_methods = sorted(
            [
                "get",
                "post",
                "options",
                "put",
                "patch",
                "delete",
                "post_batch",
                "put_batch",
                "patch_batch",
                "delete_batch",
                "pages",
                "api_params",
                "path",
                "resource",
                "resource_name",
                "session",
            ]
        )
        assert len(dir_var) == len(expected_methods)
        for attr, expected in zip(dir_var, expected_methods):
            assert attr == expected

    async def test_request_with_context_manager(self, mocked):
        async with SimpleClient() as client:
            next_url = "http://api.example.org/next_batch"
            data = {"data": [{"key": "value"}], "paging": {"next": next_url}}
            mocked.get(
                client.test().path,
                body=json.dumps(data),
                status=200,
                content_type="application/json",
            )

            response = await client.test().get()

            assert response.response is not None
            assert response.status == 200

    async def test_response_executor_object_has_a_response(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        assert response.response is not None
        assert response.status == 200

    async def test_response_executor_has_a_status_code(self, mocked, client):
        data = {"data": {"key": "value"}}
        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        assert response.status == 200

    async def test_access_response_field(self, mocked, client):
        data = {"data": {"key": "value"}}
        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        assert response.data.data() == {"key": "value"}

    async def test_carries_request_kwargs_over_calls(self, mocked, client):
        data = {"data": {"key": "value"}}
        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        request_kwargs = response.request_kwargs

        assert "url" in request_kwargs
        assert "data" in request_kwargs
        assert "headers" in request_kwargs

    async def test_retry_request(self, mocked):
        error_data = {"error": "bad request test"}
        success_data = {"data": "success!"}
        async with RetryRequestClient() as client:
            for _ in range(11):
                mocked.get(
                    client.test().path,
                    body=json.dumps(error_data),
                    status=400,
                    content_type="application/json",
                )

            with pytest.raises(ClientError):
                await client.test().get()

            for _ in range(10):
                mocked.get(
                    client.test().path,
                    body=json.dumps(error_data),
                    status=400,
                    content_type="application/json",
                )

            mocked.get(
                client.test().path,
                body=json.dumps(success_data),
                status=200,
                content_type="application/json",
            )

            response = await client.test().get()

            assert response.data.data() == "success!"

            for _ in range(3):
                mocked.get(
                    client.test().path,
                    body=json.dumps(error_data),
                    status=400,
                    content_type="application/json",
                )

            mocked.get(
                client.test().path,
                body=json.dumps(success_data),
                status=200,
                content_type="application/json",
            )

            response = await client.test().get()

            assert response.data.data() == "success!"

            for _ in range(3):
                mocked.get(
                    client.test().path,
                    body=json.dumps(error_data),
                    status=403,
                    content_type="application/json",
                )

            with pytest.raises(ClientError):
                await client.test().get()

    async def test_requests(self, mocked, client):
        semaphores = (3, None)
        types_request = ("get", "post", "put", "patch", "delete")
        for semaphore, type_request in product(semaphores, types_request):
            executor = client.test()

            status = 200 if type_request == "get" else 201

            mocked_method = getattr(mocked, type_request)
            executor_method = getattr(executor, type_request)

            mocked_method(
                executor.path,
                body='{"data": {"key": "value"}}',
                status=status,
                content_type="application/json",
            )

            kwargs = {}
            if semaphore:
                kwargs.update({"semaphore": semaphore})

            response = await executor_method(**kwargs)

            result_response = {
                response.data: {"data": {"key": "value"}},
                response.data.data: {"key": "value"},
                response.data.data.key: "value",
            }

            for current_data, expected_data in result_response.items():
                check_response(current_data, expected_data, response, status)

    async def test_batch_requests(self, mocked, client):
        response_data = [
            {"data": {"key": "value"}},
            {"data": {"key": "value"}},
            {"data": {"key": "value"}},
        ]
        semaphores = (3, None)
        types_request = ("post", "put", "patch", "delete")
        for semaphore, type_request in product(semaphores, types_request):
            executor = client.test()
            mocked_method = getattr(mocked, type_request)
            executor_method = getattr(executor, type_request + "_batch")

            for row_data in response_data:
                mocked_method(
                    executor.path,
                    body=json.dumps(row_data),
                    status=201,
                    content_type="application/json",
                )

            kwargs = {"data": response_data}
            if semaphore:
                kwargs.update({"semaphore": semaphore})

            results = await executor_method(**kwargs)

            for i, response in enumerate(results):
                result_response = {
                    response.data: response_data[i],
                    response.data.data: response_data[i]["data"],
                    response.data.data.key: response_data[i]["data"]["key"],
                }
                for current_data, expected_data in result_response.items():
                    check_response(current_data, expected_data, response, 201)

            assert len(results) == len(response_data)

    async def test_pass_api_params_in_requests(self, mocked):
        semaphores = (4, None, False)
        types_request = ("get", "post", "put", "patch", "delete")

        for semaphore, type_request in product(semaphores, types_request):
            async with SimpleClient(semaphore=semaphore) as simple_client:
                executor = simple_client.test()

                status = 200 if type_request == "get" else 201

                mocked_method = getattr(mocked, type_request)
                executor_method = getattr(executor, type_request)

                mocked_method(
                    executor.path,
                    body='{"data": {"key": "value"}}',
                    status=status,
                    content_type="application/json",
                )

                kwargs = {}

                response = await executor_method(**kwargs)

                result_response = {
                    response.data: {"data": {"key": "value"}},
                    response.data.data: {"key": "value"},
                    response.data.data.key: "value",
                }

                for current_data, expected_data in result_response.items():
                    check_response(current_data, expected_data, response, status)
                    assert response.api_params.get("semaphore") == semaphore

    async def test_pass_api_params_in_batch_requests(self, mocked):
        response_data = [
            {"data": {"key": "value"}},
            {"data": {"key": "value"}},
            {"data": {"key": "value"}},
        ]

        semaphores = (4, None, False)
        types_request = ("post", "put", "patch", "delete")

        for semaphore, type_request in product(semaphores, types_request):
            async with SimpleClient(semaphore=semaphore) as simple_client:
                executor = simple_client.test()
                mocked_method = getattr(mocked, type_request)
                executor_method = getattr(executor, type_request + "_batch")

                for row_data in response_data:
                    mocked_method(
                        executor.path,
                        body=json.dumps(row_data),
                        status=201,
                        content_type="application/json",
                    )

                kwargs = {"data": response_data}
                if semaphore:
                    kwargs.update({"semaphore": semaphore})

                results = await executor_method(**kwargs)

                for i, response in enumerate(results):
                    result_response = {
                        response.data: response_data[i],
                        response.data.data: response_data[i]["data"],
                        response.data.data.key: response_data[i]["data"]["key"],
                    }
                    for current_data, expected_data in result_response.items():
                        check_response(current_data, expected_data, response, 201)
                        assert response.api_params.get("semaphore") == semaphore

                assert len(results) == len(response_data)


class TestTapiocaClientExecutorIteratorFeatures:
    async def test_simple_pages_iterator(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["paging"]["next"] = ""
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        await check_pages_responses(response, total_pages=2)

    async def test_simple_pages_with_max_pages_iterator(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}
        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["data"].append({"key": "value"})
        data["data"].append({"key": "value"})
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["paging"]["next"] = ""
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        await check_pages_responses(response, total_pages=7, max_pages=3)

    async def test_simple_pages_with_max_items_iterator(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}
        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["data"].append({"key": "value"})
        data["data"].append({"key": "value"})
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["paging"]["next"] = ""
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        await check_pages_responses(response, total_pages=3, max_items=3)

    async def test_simple_pages_with_max_pages_and_max_items_iterator(
        self, mocked, client
    ):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["data"].append({"key": "value"})
        data["data"].append({"key": "value"})
        data["paging"]["next"] = ""
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        await check_pages_responses(response, total_pages=3, max_pages=2, max_items=3)

    async def test_simple_pages_max_pages_zero_iterator(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["paging"]["next"] = ""
        mocked.add(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        await check_pages_responses(response, total_pages=0, max_pages=0)

    async def test_simple_pages_max_items_zero_iterator(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["paging"]["next"] = ""
        mocked.add(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        await check_pages_responses(response, total_pages=0, max_items=0)

    async def test_simple_pages_max_pages_ans_max_items_zero_iterator(
        self, mocked, client
    ):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["paging"]["next"] = ""
        mocked.add(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        await check_pages_responses(response, total_pages=0, max_pages=0, max_items=0)

    async def test_pages_iterator_with_client_error(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        mocked.get(
            next_url,
            body=json.dumps(data),
            status=408,
            content_type="application/json",
        )

        data["paging"]["next"] = ""
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()
        result_response = {
            response.data: {
                "data": [{"key": "value"}],
                "paging": {"next": "http://api.example.org/next_batch"},
            },
            response.data.data: [{"key": "value"}],
            response.data.paging: {"next": "http://api.example.org/next_batch"},
            response.data.paging.next: "http://api.example.org/next_batch",
        }
        for current_data, expected_data in result_response.items():
            check_response(current_data, expected_data, response)

        iterations_count = 0
        with pytest.raises(ClientError):
            async for item in response().pages():
                result_page = {item.data: {"key": "value"}, item.data.key: "value"}
                for current_data, expected_data in result_page.items():
                    check_response(current_data, expected_data, response)
                iterations_count += 1
        assert iterations_count == 2

    async def test_pages_iterator_with_server_error(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}
        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        mocked.get(
            next_url,
            body=json.dumps(data),
            status=504,
            content_type="application/json",
        )

        data["paging"]["mext"] = ""
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()
        result_response = {
            response.data: {
                "data": [{"key": "value"}],
                "paging": {"next": "http://api.example.org/next_batch"},
            },
            response.data.data: [{"key": "value"}],
            response.data.paging: {"next": "http://api.example.org/next_batch"},
            response.data.paging.next: "http://api.example.org/next_batch",
        }
        for current_data, expected_data in result_response.items():
            check_response(current_data, expected_data, response)

        iterations_count = 0
        with pytest.raises(ServerError):
            async for item in response().pages():
                result_page = {item.data: {"key": "value"}, item.data.key: "value"}
                for current_data, expected_data in result_page.items():
                    check_response(current_data, expected_data, response)
                iterations_count += 1
        assert iterations_count == 2

    async def test_pages_iterator_with_error_on_single_page(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["data"] = [{}]
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=204,
            content_type="application/json",
        )

        data["data"] = [{"key": "value"}]
        data["paging"]["next"] = ""
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()
        result_response = {
            response.data: {
                "data": [{"key": "value"}],
                "paging": {"next": "http://api.example.org/next_batch"},
            },
            response.data.data: [{"key": "value"}],
            response.data.paging: {"next": "http://api.example.org/next_batch"},
            response.data.paging.next: "http://api.example.org/next_batch",
        }
        for current_data, expected_data in result_response.items():
            check_response(current_data, expected_data, response)

        iterations_count = 0
        async for item in response().pages():
            if iterations_count == 2:
                status = 204
                result_page = {item.data: {}}
            else:
                status = 200
                result_page = {item.data: {"key": "value"}, item.data.key: "value"}
            for current_data, expected_data in result_page.items():
                check_response(current_data, expected_data, item, status)
            iterations_count += 1
        assert iterations_count == 4


class TestTapiocaClientResponse:
    async def test_available_attributes(self, mocked, client):
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}

        mocked.get(
            client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )
        response = await client.test().get()
        dir_var = dir(response)
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
        assert len(dir_var) == len(expected_methods)
        for attr, expected in zip(dir_var, expected_methods):
            assert attr == expected

    async def test_callable_executor_from_response(self, mocked, client):
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


class TestTokenRefreshing:
    @pytest.fixture
    def possible_false_values(self):
        yield False, None, 1, 0, "511", -22, 41, [], (), set(), [41], {"key": "value"}

    async def test_not_token_refresh_client_propagates_client_error(
        self, mocked, client
    ):
        no_refresh_client = client

        mocked.post(
            no_refresh_client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await no_refresh_client.test().post()

    async def test_disable_token_refreshing(self, mocked, possible_false_values):
        async with TokenRefreshClient(token="token") as client:
            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )

            with pytest.raises(ClientError):
                await client.test().post()

        for refresh_token in possible_false_values:
            async with TokenRefreshClient(
                token="token", refresh_token=refresh_token
            ) as client:
                mocked.post(
                    client.test().path,
                    callback=callback_401,
                    content_type="application/json",
                )

                with pytest.raises(ClientError):
                    await client.test().post()

            async with TokenRefreshClient(token="token") as client:
                mocked.post(
                    client.test().path,
                    callback=callback_401,
                    content_type="application/json",
                )

                with pytest.raises(ClientError):
                    await client.test().post(refresh_token=refresh_token)

    async def test_token_expired_automatically_refresh_authentication(self, mocked):
        async with TokenRefreshClient(token="token") as client:
            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )

            mocked.post(
                client.test().path,
                callback=callback_201,
                content_type="application/json",
            )

            response = await client.test().post(refresh_token=True)

            # refresh_authentication method should be able to update api_params
            assert response.api_params["token"] == "new_token"

            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )
            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )

            # check that the refresh_token flag is not cyclic
            with pytest.raises(ClientError):
                await client.test().post(refresh_token=True)

        async with TokenRefreshClient(token="token", refresh_token=True) as client:
            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )

            mocked.post(
                client.test().path,
                callback=callback_201,
                content_type="application/json",
            )

            response = await client.test().post()

            # refresh_authentication method should be able to update api_params
            assert response.api_params["token"] == "new_token"

            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )
            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )

            # check that the refresh_token flag is not cyclic
            with pytest.raises(ClientError):
                await client.test().post()

    async def test_token_expired_automatically_refresh_authentication_by_default(
        self, mocked
    ):
        async with TokenRefreshByDefaultClient(token="token") as client:
            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )

            mocked.post(
                client.test().path,
                callback=callback_201,
                content_type="application/json",
            )

            response = await client.test().post()

            # refresh_authentication method should be able to update api_params
            assert response._api_params["token"] == "new_token"

            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )
            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )

            # check that the refresh_token flag is not cyclic
            with pytest.raises(ClientError):
                await client.test().post()

    async def test_raises_error_if_refresh_authentication_method_returns_false_value(
        self, mocked, possible_false_values
    ):
        async with FailTokenRefreshClient(token="token") as client:
            mocked.post(
                client.test().path,
                callback=callback_401,
                content_type="application/json",
            )

            with pytest.raises(ClientError):
                await client.test().post()

        for refresh_token in (True, *possible_false_values):
            async with FailTokenRefreshClient(
                token="token", refresh_token=refresh_token
            ) as client:
                mocked.post(
                    client.test().path,
                    callback=callback_401,
                    content_type="application/json",
                )

                with pytest.raises(ClientError):
                    await client.test().post()

            async with FailTokenRefreshClient(token="token") as client:
                mocked.post(
                    client.test().path,
                    callback=callback_401,
                    content_type="application/json",
                )

                with pytest.raises(ClientError):
                    await client.test().post(refresh_token=refresh_token)


class TestProcessData:
    async def test_in_operator(self, mocked, client):
        mocked.get(
            client.test().path,
            body='{"data": 1, "other": 2}',
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        assert "data" in response.data
        assert "other" in response.data
        assert "wat" not in response.data

    async def test_transform_came_case_in_snake_case(self, mocked, client):
        next_url = "http://api.example.org/next_batch"

        response_data = {
            "data": {
                "key_snake": "value",
                "camelCase": "data in camel case",
                "NormalCamelCase": "data in camel case",
            },
            "paging": {"next": f"{next_url}"},
        }
        mocked.add(
            client.test().path,
            body=json.dumps(response_data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        assert response.data() == response_data

        assert response.data.paging.next() == next_url
        assert response.data.data.key_snake() == "value"
        assert response.data.data.camel_case() == "data in camel case"
        assert response.data.data.normal_camel_case() == "data in camel case"

    async def test_should_be_able_to_access_by_index(self, mocked, client):
        response_data = ["a", "b", "c"]
        mocked.get(
            client.test().path,
            body=json.dumps(response_data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        assert response.data() == response_data

        for row_1, row_2 in zip(response.data, response_data):
            assert row_1() == row_2

        assert response.data[0]() == "a"
        assert response.data[1]() == "b"
        assert response.data[2]() == "c"

    async def test_accessing_index_out_of_bounds_should_raise_index_error(
        self, mocked, client
    ):
        response_data = ["a", "b", "c"]
        mocked.get(
            client.test().path,
            body=json.dumps(response_data),
            status=200,
            content_type="application/json",
        )

        response = await client.test().get()

        with pytest.raises(IndexError):
            response.data[3]

    async def test_accessing_empty_list_should_raise_index_error(self, mocked, client):
        mocked.get(
            client.test().path, body="[]", status=200, content_type="application/json"
        )

        response = await client.test().get()

        with pytest.raises(IndexError):
            response.data[3]


class TestParsers:
    @pytest_asyncio.fixture
    async def func_parser_client(self):
        async with FuncParserClient() as client:
            yield client

    @pytest_asyncio.fixture
    async def static_method_parser_client(self):
        async with StaticMethodParserClient() as client:
            yield client

    @pytest_asyncio.fixture
    async def class_method_parser_client(self):
        async with ClassMethodParserClient() as client:
            yield client

    @pytest_asyncio.fixture
    async def class_parser_client(self):
        async with ClassParserClient() as client:
            yield client

    @pytest_asyncio.fixture
    async def dict_parser_client(self):
        async with DictParserClient() as client:
            yield client

    async def test_parsers_not_found(self, mocked, func_parser_client):
        data = ["a", "b", "c"]
        mocked.get(
            func_parser_client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )
        response = await func_parser_client.test().get()

        with pytest.raises(AttributeError):
            response.data.blablabla()

    async def test_func_parser(self, mocked, func_parser_client):
        data = ["a", "b", "c"]
        mocked.get(
            func_parser_client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )
        response = await func_parser_client.test().get()

        assert response.data.foo_parser() == ["a", "b", "c"]
        assert response.data.foo_parser(0) == "a"
        assert response.data.foo_parser(1) == "b"
        assert response.data.foo_parser(2) == "c"
        with pytest.raises(IndexError):
            response.data.foo_parser(3)

    async def test_static_method_parser(self, mocked, static_method_parser_client):
        data = ["a", "b", "c"]
        mocked.get(
            static_method_parser_client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )
        response = await static_method_parser_client.test().get()

        assert response.data.foo() == ["a", "b", "c"]
        assert response.data.foo(0) == "a"
        assert response.data.foo(1) == "b"
        assert response.data.foo(2) == "c"
        with pytest.raises(IndexError):
            response.data.foo(3)

    async def test_class_method_parser(self, mocked, class_method_parser_client):
        data = ["a", "b", "c"]
        mocked.get(
            class_method_parser_client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )
        response = await class_method_parser_client.test().get()

        assert response.data.spam() == ["a", "b", "c"]
        assert response.data.spam(0) == "a"
        assert response.data.spam(1) == "b"
        assert response.data.spam(2) == "c"
        with pytest.raises(IndexError):
            response.data.spam(3)

    async def test_class_parser(self, mocked, class_parser_client):
        data = ["a", "b", "c"]
        mocked.get(
            class_parser_client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )
        response = await class_parser_client.test().get()

        parser = response.data.foo_parser()
        assert parser.bar() == ["a", "b", "c"]
        assert parser.bar(0) == "a"
        assert parser.bar(1) == "b"
        assert parser.bar(2) == "c"
        with pytest.raises(IndexError):
            parser.bar(3)

    async def test_dict_parser(self, mocked, dict_parser_client):
        data = ["a", "b", "c"]
        mocked.get(
            dict_parser_client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )
        response = await dict_parser_client.test().get()

        assert response.data.func_parser() == ["a", "b", "c"]
        assert response.data.func_parser(1) == "b"

        assert response.data.static_method_parser() == ["a", "b", "c"]
        assert response.data.static_method_parser(1) == "b"

        assert response.data.class_parser().bar() == ["a", "b", "c"]
        assert response.data.class_parser().bar(1) == "b"
