from decimal import Decimal

import orjson
import pytest
import pytest_asyncio
from yarl import URL

from aiotapioca import BaseSerializer, SimpleSerializer

from .clients import SerializerClient, SimpleClient


@pytest.fixture
def serializer():
    yield SimpleSerializer()


@pytest_asyncio.fixture
async def serializer_client():
    async with SerializerClient() as c:
        yield c


@pytest_asyncio.fixture
async def client_serializer_class():
    async with SimpleClient(serializer_class=SimpleSerializer) as c:
        yield c


"""
test serializer
"""


def test_passing_serializer_on_instatiation(client_serializer_class):
    serializer = client_serializer_class._api.serializer
    assert isinstance(serializer, BaseSerializer)


async def test_external_serializer_is_passed_along_clients(
    mocked, client_serializer_class
):
    mocked.get(
        client_serializer_class.test().path,
        body='{"date": "2014-11-13T14:53:18.694072+00:00"}',
        status=200,
        content_type="application/json",
    )
    response = await client_serializer_class.test().get()
    assert response._api.serializer.__class__ == SimpleSerializer


def test_serializer_client_adapter_has_serializer(serializer_client):
    serializer = serializer_client._api.serializer
    assert isinstance(serializer, BaseSerializer)


async def test_executor_dir_returns_serializer_methods(mocked, serializer_client):
    mocked.get(
        serializer_client.test().path,
        body='{"date": "2014-11-13T14:53:18.694072+00:00"}',
        status=200,
        content_type="application/json",
    )

    response = await serializer_client.test().get()

    e_dir = dir(response.data)

    assert "to_decimal" in e_dir


"""
test deserialization
"""


async def test_convert_to_decimal(mocked, serializer_client):
    mocked.get(
        serializer_client.test().path,
        body='{"decimal_value": "10.51"}',
        status=200,
        content_type="application/json",
    )

    response = await serializer_client.test().get()
    assert response.data.decimal_value.to_decimal() == Decimal("10.51")


async def test_call_non_existent_conversion(mocked, serializer_client):
    mocked.get(
        serializer_client.test().path,
        body='{"any_data": "%#ˆ$&"}',
        status=200,
        content_type="application/json",
    )

    response = await serializer_client.test().get()
    with pytest.raises(NotImplementedError):
        response.data.any_data.to_blablabla()


async def test_call_conversion_with_no_serializer(mocked, client):
    mocked.get(
        client.test().path,
        body='{"any_data": "%#ˆ$&"}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()
    with pytest.raises(NotImplementedError):
        response.data.any_data.to_datetime()


async def test_pass_kwargs(mocked, serializer_client):
    mocked.get(
        serializer_client.test().path,
        body='{"decimal_value": "10.51"}',
        status=200,
        content_type="application/json",
    )

    response = await serializer_client.test().get()

    assert response.data.decimal_value.to_kwargs(some_key="some value") == {
        "some_key": "some value"
    }


"""
test serialization
"""


def test_serialize_int(serializer):
    data = 1
    serialized = serializer.serialize(data)
    assert serialized == data


def test_serialize_str(serializer):
    data = "the str"
    serialized = serializer.serialize(data)
    assert serialized == data


def test_serialize_float(serializer):
    data = 1.23
    serialized = serializer.serialize(data)
    assert serialized == data


def test_serialize_none(serializer):
    data = None
    serialized = serializer.serialize(data)
    assert serialized == data


def test_serialization_of_simple_dict(serializer):
    data = {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3",
    }
    serialized = serializer.serialize(data)
    assert serialized == data


def test_serialization_of_simple_list(serializer):
    data = [1, 2, 3, 4, 5]
    serialized = serializer.serialize(data)
    assert serialized == data


def test_serialization_of_nested_list_in_dict(serializer):
    data = {
        "key1": [1, 2, 3, 4, 5],
        "key2": [1],
        "key3": [1, 2, 5],
    }
    serialized = serializer.serialize(data)
    assert serialized == data


def test_multi_level_serializations(serializer):
    data = [
        {"key1": [1, 2, 3, 4, 5]},
        {"key2": [1]},
        {"key3": [1, 2, 5]},
    ]
    serialized = serializer.serialize(data)
    assert serialized == data


def test_decimal_serialization(serializer):
    data = {"key": [Decimal("1.0"), Decimal("1.1"), Decimal("1.2")]}
    serialized = serializer.serialize(data)
    assert serialized == {"key": ["1.0", "1.1", "1.2"]}

