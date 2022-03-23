import arrow
import json
import pytest
from decimal import Decimal
from yarl import URL
from pydantic import BaseModel

from aiotapioca import BaseSerializer, SimpleSerializer
from .clients import CustomModel


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
        client_serializer_class.test().data,
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
        serializer_client.test().data,
        body='{"date": "2014-11-13T14:53:18.694072+00:00"}',
        status=200,
        content_type="application/json",
    )

    response = await serializer_client.test().get()

    e_dir = dir(response())

    assert "to_datetime" in e_dir
    assert "to_decimal" in e_dir


async def test_request_with_data_serialization(mocked, serializer_client):
    mocked.post(
        serializer_client.test().data,
        body="{}",
        status=200,
        content_type="application/json",
    )

    string_date = "2014-11-13T14:53:18.694072+00:00"
    string_decimal = "1.45"

    data = {
        "date": arrow.get(string_date).datetime,
        "decimal": Decimal(string_decimal),
    }

    await serializer_client.test().post(data=data)

    request_body = mocked.requests[("POST", URL(serializer_client.test().data))][
        0
    ].kwargs["data"]

    assert json.loads(request_body) == {"date": string_date, "decimal": string_decimal}


"""
test deserialization
"""


async def test_convert_to_decimal(mocked, serializer_client):
    mocked.get(
        serializer_client.test().data,
        body='{"decimal_value": "10.51"}',
        status=200,
        content_type="application/json",
    )

    response = await serializer_client.test().get()
    assert response.decimal_value().to_decimal() == Decimal("10.51")


async def test_convert_to_datetime(mocked, serializer_client):
    mocked.get(
        serializer_client.test().data,
        body='{"date": "2014-11-13T14:53:18.694072+00:00"}',
        status=200,
        content_type="application/json",
    )

    response = await serializer_client.test().get()
    date = response.date().to_datetime()
    assert date.year == 2014
    assert date.month == 11
    assert date.day == 13
    assert date.hour == 14
    assert date.minute == 53
    assert date.second == 18


async def test_convert_to_pydantic(mocked, pydantic_client):
    response_body = (
        '{"data": [{"key1": "value1", "key2": 123}, {"key1": "value2", "key2": 321}]}'
    )

    mocked.get(
        pydantic_client.test().data,
        body=response_body,
        status=200,
        content_type="application/json",
    )

    response = await pydantic_client.test_pydantic().get()
    data = response().to_pydantic()

    assert isinstance(data, BaseModel)
    assert data.json() == response_body


async def test_convert_to_pydantic_has_no_model_in_resource(mocked, pydantic_client):
    response_body = (
        '{"data": [{"key1": "value1", "key2": 123}, {"key1": "value2", "key2": 321}]}'
    )

    mocked.get(
        pydantic_client.test().data,
        body=response_body,
        status=200,
        content_type="application/json",
    )

    response = await pydantic_client.test().get()

    with pytest.raises(ValueError):
        response().to_pydantic()


async def test_convert_to_pydantic_pass_model_as_param(mocked, pydantic_client):
    response_body = (
        '{"data": [{"key1": "value1", "key2": 123}, {"key1": "value2", "key2": 321}]}'
    )

    mocked.get(
        pydantic_client.test().data,
        body=response_body,
        status=200,
        content_type="application/json",
    )

    response = await pydantic_client.test().get()

    data = response().to_pydantic(model=CustomModel)

    assert isinstance(data, BaseModel)
    assert data.json() == response_body


async def test_call_non_existent_conversion(mocked, serializer_client):
    mocked.get(
        serializer_client.test().data,
        body='{"any_data": "%#ˆ$&"}',
        status=200,
        content_type="application/json",
    )

    response = await serializer_client.test().get()
    with pytest.raises(NotImplementedError):
        response.any_data().to_blablabla()


async def test_call_conversion_with_no_serializer(mocked, client):
    mocked.get(
        client.test().data,
        body='{"any_data": "%#ˆ$&"}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()
    with pytest.raises(NotImplementedError):
        response.any_data().to_datetime()


async def test_pass_kwargs(mocked, serializer_client):
    mocked.get(
        serializer_client.test().data,
        body='{"decimal_value": "10.51"}',
        status=200,
        content_type="application/json",
    )

    response = await serializer_client.test().get()

    assert response.decimal_value().to_kwargs(some_key="some value") == {
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


def test_datetime_serialization(serializer):
    string_date = "2014-11-13T14:53:18.694072+00:00"
    data = [arrow.get(string_date).datetime]
    serialized = serializer.serialize(data)
    assert serialized == [string_date]
