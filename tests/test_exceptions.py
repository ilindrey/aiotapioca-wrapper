import aiohttp
import pytest

from aiotapioca.exceptions import ClientError, ResponseProcessException, ServerError

from .clients import SimpleClientAdapter


async def test_exception_contain_data(mocked, client):
    mocked.get(
        client.test().path,
        body='{"data": {"key": "value"}}',
        status=400,
        content_type="application/json",
    )
    try:
        await client.test().get()
    except ResponseProcessException as ex:
        assert ex.data == {"data": {"key": "value"}}


async def test_exception_contain_response(mocked, client):
    mocked.get(client.test().path, body="", status=400, content_type="application/json")
    try:
        await client.test().get()
    except ResponseProcessException as ex:
        assert type(ex.response) is aiohttp.ClientResponse
        assert ex.response.status == 400


async def test_exception_message(mocked, client):
    mocked.get(client.test().path, body="", status=400, content_type="application/json")
    try:
        await client.test().get()
    except ResponseProcessException as ex:
        assert ex.message == "Response: GET [400] https://api.example.org/test/"


async def test_adapter_raises_response_process_exception_on_400s(mocked, client):
    mocked.get(
        client.test().path,
        body='{"errors": "Server Error"}',
        status=400,
        content_type="application/json",
    )
    async with aiohttp.ClientSession() as session:
        response = await session.get(client.test().path)
    with pytest.raises(ResponseProcessException):
        await SimpleClientAdapter().process_response(response)


async def test_adapter_raises_response_process_exception_on_500s(mocked, client):
    mocked.get(
        client.test().path,
        body='{"errors": "Server Error"}',
        status=500,
        content_type="application/json",
    )
    async with aiohttp.ClientSession() as session:
        response = await session.get(client.test().path)
    with pytest.raises(ResponseProcessException):
        await SimpleClientAdapter().process_response(response)


async def test_thrown_tapioca_exception_with_client_error_data(mocked, client):
    mocked.get(
        client.test().path,
        body='{"error": "bad request test"}',
        status=400,
        content_type="application/json",
    )
    with pytest.raises(ClientError) as exception:
        await client.test().get()
    assert "bad request test" in exception.value.message


async def test_thrown_tapioca_exception_with_server_error_data(mocked, client):
    mocked.get(
        client.test().path,
        body='{"error": "server error test"}',
        status=500,
        content_type="application/json",
    )
    with pytest.raises(ServerError) as exception:
        await client.test().get()
    assert "server error test" in exception.value.message
