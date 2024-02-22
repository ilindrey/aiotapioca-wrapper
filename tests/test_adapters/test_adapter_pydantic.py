import json
from dataclasses import asdict, dataclass, is_dataclass
from itertools import product
from typing import Any, Dict, List

import pytest

from aiotapioca import TapiocaAdapterPydantic, generate_wrapper_from_adapter


try:
    import pydantic
except ImportError:
    pytest.skip(reason="pydantic not installed", allow_module_level=True)


class Detail(pydantic.BaseModel):
    key1: str
    key2: int


class CustomModel(pydantic.BaseModel):
    data: List[Detail]


class RootModel(pydantic.RootModel):
    root: List[Detail]


@pydantic.dataclasses.dataclass
class DetailDT:
    key1: str
    key2: int


@pydantic.dataclasses.dataclass
class CustomModelDT:
    data: List[DetailDT]


@dataclass
class NotPydanticDT:
    data: List[DetailDT]


class PydanticDefaultClientAdapter(TapiocaAdapterPydantic):
    api_root = "https://api.example.org"
    resource_mapping: Dict[str, Any] = {
        "test": {
            "resource": "test/",
            "docs": "http://www.example.org",
            "pydantic_models": {
                "request": CustomModel,
                "response": {CustomModel: "GET"},
            },
        },
        "test_root": {
            "resource": "test/",
            "docs": "http://www.example.org",
            "pydantic_models": {
                "request": {Detail: ["POST"]},
                "response": {RootModel: "GET"},
            },
        },
        "test_dataclass": {
            "resource": "test/",
            "docs": "http://www.example.org",
            "pydantic_models": {
                "request": CustomModelDT,
                "response": {CustomModelDT: ["GET"]},
            },
        },
    }


PydanticDefaultClient = generate_wrapper_from_adapter(PydanticDefaultClientAdapter)


class PydanticForcedClientAdapter(PydanticDefaultClientAdapter):
    forced_to_have_model = True
    resource_mapping: Dict[str, Any] = {
        "test_not_found": {
            "resource": "test/",
            "docs": "http://www.example.org",
            "pydantic_models": None,
        },
        "test_bad_pydantic_model": {
            "resource": "test/",
            "docs": "http://www.example.org",
            "pydantic_models": 100500,
        },
        "test_bad_dataclass_model": {
            "resource": "test/",
            "docs": "http://www.example.org",
            "pydantic_models": NotPydanticDT,
        },
    }


PydanticForcedClient = generate_wrapper_from_adapter(PydanticForcedClientAdapter)


def test_pydantic_model_get_pydantic_model():
    from aiotapioca.adapters.mixins import import_pydantic

    import_pydantic()

    resource = {
        "resource": "test/",
        "docs": "http://www.example.org",
        "pydantic_models": CustomModelDT,
    }

    model = TapiocaAdapterPydantic().get_pydantic_model("response", resource, "GET")
    assert model == CustomModelDT

    resource["pydantic_models"] = CustomModel
    model = TapiocaAdapterPydantic().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {CustomModel: "GET"}
    model = TapiocaAdapterPydantic().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {CustomModel: ["GET"]}
    model = TapiocaAdapterPydantic().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"response": CustomModel}
    model = TapiocaAdapterPydantic().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"response": {CustomModel: "GET"}}
    model = TapiocaAdapterPydantic().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"response": {CustomModel: ["POST"]}}
    model = TapiocaAdapterPydantic().get_pydantic_model("response", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {"response": {CustomModel: ["GET"], Detail: None}}
    model = TapiocaAdapterPydantic().get_pydantic_model("response", resource, "POST")
    assert model == Detail

    resource["pydantic_models"] = {"response": {CustomModel: ["GET"], Detail: None}}
    model = TapiocaAdapterPydantic().get_pydantic_model("request", resource, "POST")
    assert model is None

    resource["pydantic_models"] = CustomModel
    model = TapiocaAdapterPydantic().get_pydantic_model("request", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {CustomModel: "POST"}
    model = TapiocaAdapterPydantic().get_pydantic_model("request", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {CustomModel: ["GET"]}
    model = TapiocaAdapterPydantic().get_pydantic_model("request", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"request": CustomModel}
    model = TapiocaAdapterPydantic().get_pydantic_model("request", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {"request": {CustomModel: "GET"}}
    model = TapiocaAdapterPydantic().get_pydantic_model("request", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"request": {CustomModel: ["POST"]}}
    model = TapiocaAdapterPydantic().get_pydantic_model("request", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {"request": {CustomModel: ["GET"], Detail: None}}
    model = TapiocaAdapterPydantic().get_pydantic_model("request", resource, "POST")
    assert model == Detail

    resource["pydantic_models"] = {"response": {CustomModel: ["GET"], Detail: None}}
    model = TapiocaAdapterPydantic().get_pydantic_model("request", resource, "POST")
    assert model is None


async def test_pydantic_model_not_found(mocked):
    async with PydanticForcedClient() as client:
        mocked.get(
            client.test_not_found().path,
            body="{}",
            status=200,
            content_type="application/json",
        )
        with pytest.raises(ValueError):
            await client.test_not_found().get()


async def test_bad_pydantic_model(mocked):
    async with PydanticForcedClient() as client:
        mocked.get(
            client.test_bad_pydantic_model().path,
            body="{}",
            status=200,
            content_type="application/json",
        )
        with pytest.raises(ValueError):
            await client.test_bad_pydantic_model().get()


async def test_bad_dataclass_model(mocked):
    async with PydanticForcedClient() as client:
        mocked.get(
            client.test_bad_dataclass_model().path,
            body="{}",
            status=200,
            content_type="application/json",
        )
        with pytest.raises(TypeError):
            await client.test_bad_dataclass_model().get()


async def test_pydantic_mixin_response_to_native(mocked):
    response_body_root = [
        {"key1": "value1", "key2": 123},
        {"key1": "value2", "key2": 321},
    ]
    response_body = {"data": response_body_root}

    validate_data_received_list = [True, False]
    validate_data_sending_list = [True, False]
    extract_root_list = [True, False]
    convert_to_dict_list = [True, False]

    for validate_received, validate_sending, extract, convert in product(
        validate_data_received_list,
        validate_data_sending_list,
        extract_root_list,
        convert_to_dict_list,
    ):

        class PidanticClientAdapter(PydanticDefaultClientAdapter):
            validate_data_received = validate_received
            validate_data_sending = validate_sending
            extract_root = extract
            convert_to_dict = convert

        pydantic_client = generate_wrapper_from_adapter(PidanticClientAdapter)

        async with pydantic_client() as client:
            mocked.get(
                client.test().path,
                body=json.dumps(response_body),
                status=200,
                content_type="application/json",
            )
            response = await client.test().get()
            if convert or not validate_received:
                assert isinstance(response.data(), dict)
                assert response.data() == response_body
            else:
                assert isinstance(response.data(), pydantic.BaseModel)
                assert response.data().model_dump() == response_body

            mocked.get(
                client.test_root().path,
                body=json.dumps(response_body_root),
                status=200,
                content_type="application/json",
            )
            response = await client.test_root().get()
            data = response.data()
            if extract:
                assert isinstance(data, list)
            else:
                if not validate_received or convert:
                    assert isinstance(data, list)
                else:
                    assert isinstance(data, pydantic.BaseModel)
                    data = data.root
            for response_data, expected_data in zip(data, response_body_root):
                if convert or not validate_received:
                    assert isinstance(response_data, dict)
                    assert response_data == expected_data
                else:
                    assert isinstance(response_data, pydantic.BaseModel)
                    assert response_data.model_dump() == expected_data

            mocked.get(
                client.test_dataclass().path,
                body=json.dumps(response_body),
                status=200,
                content_type="application/json",
            )
            response = await client.test_dataclass().get()
            if convert or not validate_received:
                assert isinstance(response.data(), dict)
                assert response.data() == response_body
            else:
                assert is_dataclass(response.data())
                assert asdict(response.data()) == response_body


async def test_pydantic_mixin_format_data_to_request(mocked):
    response_body_root = [
        {"key1": "value1", "key2": 123},
        {"key1": "value2", "key2": 321},
    ]
    response_body = {"data": response_body_root}

    validate_data_received_list = [True, False]
    validate_data_sending_list = [True, False]
    extract_root_list = [True, False]
    convert_to_dict_list = [True, False]

    for validate_received, validate_sending, extract, convert in product(
        validate_data_received_list,
        validate_data_sending_list,
        extract_root_list,
        convert_to_dict_list,
    ):

        class PidanticClientAdapter(PydanticDefaultClientAdapter):
            validate_data_received = validate_received
            validate_data_sending = validate_sending
            extract_root = extract
            convert_to_dict = convert

        pydantic_client = generate_wrapper_from_adapter(PidanticClientAdapter)

        async with pydantic_client() as client:
            mocked.post(
                client.test().path,
                body='{"id": 100500}',
                status=200,
                content_type="application/json",
            )
            if validate_sending:
                response = await client.test().post(data=response_body)
                assert response.data() == {"id": 100500}
            else:
                data = CustomModel.model_validate(response_body)
                response = await client.test().post(data=data)
                assert response.data() == {"id": 100500}

            if validate_sending:
                for _ in range(len(response_body_root)):
                    mocked.post(
                        client.test_root().path,
                        body='{"id": 100500}',
                        status=200,
                        content_type="application/json",
                    )
                responses = await client.test_root().post_batch(data=response_body_root)
                assert len(responses) == len(response_body_root)
                for response in responses:
                    assert response.data() == {"id": 100500}
            else:
                data = RootModel.model_validate(response_body_root)
                for _ in range(len(data.root)):
                    mocked.post(
                        client.test_root().path,
                        body='{"id": 100500}',
                        status=200,
                        content_type="application/json",
                    )
                responses = await client.test_root().post_batch(data=data.root)
                assert len(responses) == len(data.root)
                for response in responses:
                    assert response.data() == {"id": 100500}

            mocked.post(
                client.test().path,
                body='{"id": 100500}',
                status=200,
                content_type="application/json",
            )
            if validate_sending:
                response = await client.test_dataclass().post(data=response_body)
                assert response.data() == {"id": 100500}
            else:
                data = pydantic.TypeAdapter(CustomModelDT).validate_python(
                    response_body
                )
                response = await client.test_dataclass().post(data=data)
                assert response.data() == {"id": 100500}

    class PidanticClientAdapter(PydanticDefaultClientAdapter):
        forced_to_have_model = True
        validate_data_sending = False
        validate_data_received = False

    pydantic_client = generate_wrapper_from_adapter(PidanticClientAdapter)

    async with pydantic_client() as client:
        for _ in range(len(response_body_root)):
            mocked.post(
                client.test_root().path,
                body='{"id": 100500}',
                status=200,
                content_type="application/json",
            )
        responses = await client.test_root().post_batch(data=response_body_root)
        assert len(responses) == len(response_body_root)
        for response in responses:
            assert response.data() == {"id": 100500}
