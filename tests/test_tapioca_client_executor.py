import json

import pytest

from aiotapioca import ProcessData, TapiocaClientResponse, generate_wrapper_from_adapter
from aiotapioca.exceptions import ClientError, ServerError

from .client import SimpleClient, SimpleClientAdapter


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


class RetryRequestClientAdapter(SimpleClientAdapter):
    def retry_request(self, exception, *args, **kwargs):
        return kwargs["response"].status == 400


RetryRequestClient = generate_wrapper_from_adapter(RetryRequestClientAdapter)


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

    @pytest.mark.parametrize(
        "semaphore,type_request",
        (
            (4, "post"),
            (4, "put"),
            (4, "patch"),
            (4, "delete"),
            (None, "post"),
            (None, "put"),
            (None, "patch"),
            (None, "delete"),
        ),
    )
    async def test_requests(self, mocked, client, semaphore, type_request):
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

    @pytest.mark.parametrize(
        "semaphore,type_request",
        (
            (4, "post"),
            (4, "put"),
            (4, "patch"),
            (4, "delete"),
            (None, "post"),
            (None, "put"),
            (None, "patch"),
            (None, "delete"),
        ),
    )
    async def test_batch_requests(self, mocked, client, semaphore, type_request):
        response_data = [
            {"data": {"key": "value"}},
            {"data": {"key": "value"}},
            {"data": {"key": "value"}},
        ]
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

    @pytest.mark.parametrize(
        "semaphore,type_request",
        (
            (4, "get"),
            (4, "post"),
            (4, "put"),
            (4, "patch"),
            (4, "delete"),
            (None, "get"),
            (None, "post"),
            (None, "put"),
            (None, "patch"),
            (None, "delete"),
            (False, "get"),
            (False, "post"),
            (False, "put"),
            (False, "patch"),
            (False, "delete"),
        ),
    )
    async def test_pass_api_params_in_requests(self, mocked, semaphore, type_request):
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

    @pytest.mark.parametrize(
        "semaphore,type_request",
        (
            (4, "post"),
            (4, "put"),
            (4, "patch"),
            (4, "delete"),
            (None, "post"),
            (None, "put"),
            (None, "patch"),
            (None, "delete"),
            (False, "post"),
            (False, "put"),
            (False, "patch"),
            (False, "delete"),
        ),
    )
    async def test_pass_api_params_in_batch_requests(
        self, mocked, semaphore, type_request
    ):
        response_data = [
            {"data": {"key": "value"}},
            {"data": {"key": "value"}},
            {"data": {"key": "value"}},
        ]
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
