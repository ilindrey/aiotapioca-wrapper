from aiotapioca import PydanticMixin
from .models import Detail, CustomModel, CustomModelDT


def test_pydantic_model_get_pydantic_model():

    resource = {
        "resource": "test/",
        "docs": "http://www.example.org",
        "pydantic_models": CustomModelDT,
    }

    model = PydanticMixin().get_pydantic_model("response", resource, "GET")
    assert model == CustomModelDT.__pydantic_model__

    resource["pydantic_models"] = CustomModel
    model = PydanticMixin().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {CustomModel: "GET"}
    model = PydanticMixin().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {CustomModel: ["GET"]}
    model = PydanticMixin().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"response": CustomModel}
    model = PydanticMixin().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"response": {CustomModel: "GET"}}
    model = PydanticMixin().get_pydantic_model("response", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"response": {CustomModel: ["POST"]}}
    model = PydanticMixin().get_pydantic_model("response", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {"response": {CustomModel: ["GET"], Detail: None}}
    model = PydanticMixin().get_pydantic_model("response", resource, "POST")
    assert model == Detail

    resource["pydantic_models"] = {"response": {CustomModel: ["GET"], Detail: None}}
    model = PydanticMixin().get_pydantic_model("request", resource, "POST")
    assert model is None

    resource["pydantic_models"] = CustomModel
    model = PydanticMixin().get_pydantic_model("request", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {CustomModel: "POST"}
    model = PydanticMixin().get_pydantic_model("request", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {CustomModel: ["GET"]}
    model = PydanticMixin().get_pydantic_model("request", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"request": CustomModel}
    model = PydanticMixin().get_pydantic_model("request", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {"request": {CustomModel: "GET"}}
    model = PydanticMixin().get_pydantic_model("request", resource, "GET")
    assert model == CustomModel

    resource["pydantic_models"] = {"request": {CustomModel: ["POST"]}}
    model = PydanticMixin().get_pydantic_model("request", resource, "POST")
    assert model == CustomModel

    resource["pydantic_models"] = {"request": {CustomModel: ["GET"], Detail: None}}
    model = PydanticMixin().get_pydantic_model("request", resource, "POST")
    assert model == Detail

    resource["pydantic_models"] = {"response": {CustomModel: ["GET"], Detail: None}}
    model = PydanticMixin().get_pydantic_model("request", resource, "POST")
    assert model is None
