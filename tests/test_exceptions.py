import pytest
import aiohttp

from aiotapioca.exceptions import (
    ClientError,
    ServerError,
    ResponseProcessException,
    TapiocaException,
)
from aiotapioca.aiotapioca import TapiocaClient
from .clients import SimpleClientAdapter


"""
test TapiocaException
"""


async def test_exception_contain_tapioca_tester_client(mocked, client):
    mocked.get(
        client.test().data,
        body='{"data": {"key": "value"}}',
        status=400,
        content_type="application/json",
    )
    try:
        await client.test().get()
    except TapiocaException as e:
        exception = e
    assert exception.client.__class__ is TapiocaClient


async def test_exception_contain_status_code(mocked, client):
    mocked.get(client.test().data, body="", status=400, content_type="application/json")
    try:
        await client.test().get()
    except TapiocaException as e:
        exception = e
    assert exception.status == 400


async def test_exception_message(mocked, client):
    mocked.get(client.test().data, body="", status=400, content_type="application/json")
    try:
        await client.test().get()
    except TapiocaException as e:
        exception = e
    assert str(exception) == "response status code: 400"


"""
test Exceptions
"""


async def test_adapter_raises_response_process_exception_on_400s(mocked, client):
    mocked.get(
        client.test().data,
        body='{"errors": "Server Error"}',
        status=400,
        content_type="application/json",
    )
    async with aiohttp.ClientSession() as session:
        response = await session.get(client.test().data)
    with pytest.raises(ResponseProcessException):
        await SimpleClientAdapter().process_response(response)


async def test_adapter_raises_response_process_exception_on_500s(mocked, client):
    mocked.get(
        client.test().data,
        body='{"errors": "Server Error"}',
        status=500,
        content_type="application/json",
    )
    async with aiohttp.ClientSession() as session:
        response = await session.get(client.test().data)
    with pytest.raises(ResponseProcessException):
        await SimpleClientAdapter().process_response(response)


async def test_raises_request_error(mocked, client):
    mocked.get(
        client.test().data,
        body='{"data": {"key": "value"}}',
        status=400,
        content_type="application/json",
    )

    with pytest.raises(ClientError):
        await client.test().get()


async def test_raises_server_error(mocked, client):
    mocked.get(client.test().data, status=500, content_type="application/json")
    with pytest.raises(ServerError):
        await client.test().get()
