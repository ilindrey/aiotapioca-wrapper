
from itertools import product

import orjson
import pytest
from pydantic import BaseModel

from aiotapioca import generate_wrapper_from_adapter, TapiocaAdapterPydantic
from .models import (
    Detail,
    CustomModel,
    CustomModelDT,
    RootModel,
    RootModelDT,
)
from .clients import PydanticDefaultClientAdapter, PydanticForcedClient


class TestTapiocaAdapterPydantic:

    def test_pydantic_model_get_pydantic_model(self):

        resource = {
            "resource": "test/",
            "docs": "http://www.example.org",
            "pydantic_models": CustomModelDT,
        }

        model = TapiocaAdapterPydantic().get_pydantic_model("response", resource, "GET")
        assert model == CustomModelDT.__pydantic_model__

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


    async def test_pydantic_model_not_found(self, mocked):
        async with PydanticForcedClient() as client:
            mocked.get(
                client.test_not_found().path,
                body="{}",
                status=200,
                content_type="application/json",
            )
            with pytest.raises(ValueError):
                await client.test_not_found().get()


    async def test_bad_pydantic_model(self, mocked):
        async with PydanticForcedClient() as client:
            mocked.get(
                client.test_bad_pydantic_model().path,
                body="{}",
                status=200,
                content_type="application/json",
            )
            with pytest.raises(ValueError):
                await client.test_bad_pydantic_model().get()


    async def test_bad_dataclass_model(self, mocked):
        async with PydanticForcedClient() as client:
            mocked.get(
                client.test_bad_dataclass_model().path,
                body="{}",
                status=200,
                content_type="application/json",
            )
            with pytest.raises(TypeError):
                await client.test_bad_dataclass_model().get()

    async def test_pydantic_mixin_response_to_native(self, mocked):
        response_body_root = (
            '[{"key1": "value1", "key2": 123}, {"key1": "value2", "key2": 321}]'
        )
        response_body = '{"data": %s}' % response_body_root

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

            PydanticClient = generate_wrapper_from_adapter(PidanticClientAdapter)

            async with PydanticClient() as client:
                mocked.get(
                    client.test().path,
                    body=response_body,
                    status=200,
                    content_type="application/json",
                )
                response = await client.test().get()
                if convert or not validate_received:
                    assert isinstance(response.data, dict)
                    assert response.data == orjson.loads(response_body)
                else:
                    assert isinstance(response.data, BaseModel)
                    assert response.data.dict() == orjson.loads(response_body)

                mocked.get(
                    client.test_root().path,
                    body=response_body_root,
                    status=200,
                    content_type="application/json",
                )
                response = await client.test_root().get()
                data = response.data
                if extract:
                    assert isinstance(data, list)
                else:
                    if not validate_received:
                        assert isinstance(data, list)
                    elif convert:
                        assert isinstance(data, dict)
                        data = data["__root__"]
                    else:
                        assert isinstance(data, BaseModel)
                        data = data.__root__
                for response_data, expected_data in zip(
                    data, orjson.loads(response_body_root)
                ):
                    if convert or not validate_received:
                        assert isinstance(response_data, dict)
                        assert response_data == expected_data
                    else:
                        assert isinstance(response_data, BaseModel)
                        assert response_data.dict() == expected_data

                mocked.get(
                    client.test_dataclass().path,
                    body=response_body,
                    status=200,
                    content_type="application/json",
                )
                response = await client.test_dataclass().get()
                if convert or not validate_received:
                    assert isinstance(response().data, dict)
                    assert response.data == orjson.loads(response_body)
                else:
                    assert isinstance(response().data, BaseModel)
                    assert response.data.dict() == orjson.loads(response_body)

                mocked.get(
                    client.test_dataclass_root().path,
                    body=response_body_root,
                    status=200,
                    content_type="application/json",
                )
                response = await client.test_dataclass_root().get()
                data = response.data
                if extract:
                    assert isinstance(data, list)
                else:
                    if not validate_received:
                        assert isinstance(data, list)
                    elif convert:
                        assert isinstance(data, dict)
                        data = data["__root__"]
                    else:
                        assert isinstance(data, BaseModel)
                        data = data.__root__
                for response_data, expected_data in zip(
                    data, orjson.loads(response_body_root)
                ):
                    if convert or not validate_received:
                        assert isinstance(response_data, dict)
                        assert response_data == expected_data
                    else:
                        assert isinstance(response_data, BaseModel)
                        assert response_data.dict() == expected_data


    async def test_pydantic_mixin_format_data_to_request(self, mocked):
        response_body_root = (
            '[{"key1": "value1", "key2": 123}, {"key1": "value2", "key2": 321}]'
        )
        response_body = '{"data": %s}' % response_body_root

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

            PydanticClient = generate_wrapper_from_adapter(PidanticClientAdapter)

            async with PydanticClient() as client:

                mocked.post(
                    client.test().path,
                    body='{"id": 100500}',
                    status=200,
                    content_type="application/json",
                )
                if validate_sending:
                    data = orjson.loads(response_body)
                    response = await client.test().post(data=data)
                    assert response.data == {"id": 100500}
                else:
                    data = CustomModel.parse_raw(response_body)
                    response = await client.test().post(data=data)
                    assert response.data == {"id": 100500}

                if validate_sending:
                    data = orjson.loads(response_body_root)
                    for _ in range(len(data)):
                        mocked.post(
                            client.test_root().path,
                            body='{"id": 100500}',
                            status=200,
                            content_type="application/json",
                        )
                    responses = await client.test_root().post_batch(data=data)
                    assert len(responses) == len(data)
                    for response in responses:
                        assert response.data == {"id": 100500}
                else:
                    data = RootModel.parse_raw(response_body_root)
                    for _ in range(len(data.__root__)):
                        mocked.post(
                            client.test_root().path,
                            body='{"id": 100500}',
                            status=200,
                            content_type="application/json",
                        )
                    responses = await client.test_root().post_batch(data=data.__root__)
                    assert len(responses) == len(data.__root__)
                    for response in responses:
                        assert response.data == {"id": 100500}

                mocked.post(
                    client.test().path,
                    body='{"id": 100500}',
                    status=200,
                    content_type="application/json",
                )
                if validate_sending:
                    data = orjson.loads(response_body)
                    response = await client.test_dataclass().post(data=data)
                    assert response.data == {"id": 100500}
                else:
                    data = CustomModelDT.__pydantic_model__.parse_raw(response_body)
                    response = await client.test_dataclass().post(data=data)
                    assert response.data == {"id": 100500}

                if validate_sending:
                    data = orjson.loads(response_body_root)
                    for _ in range(len(data)):
                        mocked.post(
                            client.test_root().path,
                            body='{"id": 100500}',
                            status=200,
                            content_type="application/json",
                        )
                    responses = await client.test_root().post_batch(data=data)
                    assert len(responses) == len(data)
                    for response in responses:
                        assert response.data == {"id": 100500}
                else:
                    data = RootModelDT.__pydantic_model__.parse_raw(response_body_root)
                    for _ in range(len(data.__root__)):
                        mocked.post(
                            client.test_root().path,
                            body='{"id": 100500}',
                            status=200,
                            content_type="application/json",
                        )
                    responses = await client.test_root().post_batch(data=data.__root__)
                    assert len(responses) == len(data.__root__)
                    for response in responses:
                        assert response.data == {"id": 100500}

        class PidanticClientAdapter(PydanticDefaultClientAdapter):
            forced_to_have_model = True
            validate_data_sending = False
            validate_data_received = False

        PydanticClient = generate_wrapper_from_adapter(PidanticClientAdapter)

        async with PydanticClient() as client:
            data = orjson.loads(response_body_root)
            for _ in range(len(data)):
                mocked.post(
                    client.test_root().path,
                    body='{"id": 100500}',
                    status=200,
                    content_type="application/json",
                )
            responses = await client.test_root().post_batch(data=data)
            assert len(responses) == len(data)
            for response in responses:
                assert response.data == {"id": 100500}
