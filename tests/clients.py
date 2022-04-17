from dataclasses import dataclass

from pydantic import BaseModel, dataclasses

from aiotapioca import (
    generate_wrapper_from_adapter,
    TapiocaAdapter,
    JSONAdapterMixin,
    PydanticMixin,
    XMLAdapterMixin,
    SimpleSerializer,
)


class Detail(BaseModel):
    key1: str
    key2: int


class CustomModel(BaseModel):
    data: list[Detail]


class RootModel(BaseModel):
    __root__: list[Detail]


@dataclasses.dataclass
class DetailDT:
    key1: str
    key2: int


@dataclasses.dataclass
class CustomModelDT:
    data: list[Detail]


@dataclasses.dataclass
class RootModelDT:
    __root__: list[Detail]


@dataclass
class BadModelDT:
    data: list[Detail]


test = {
    "resource": "test/",
    "docs": "http://www.example.org",
}

RESOURCE_MAPPING = {
    "test": test,
    "test_pydantic_serializer": {
        **test,
        "to_pydantic": {"params": {"model": CustomModel}},
    },
    "user": {"resource": "user/{id}/", "docs": "http://www.example.org/user"},
    "resource": {
        "resource": "resource/{number}/",
        "docs": "http://www.example.org/resource",
        "spam": "eggs",
        "foo": "bar",
    },
    "another_root": {
        "resource": "another-root/",
        "docs": "http://www.example.org/another-root",
    },
}


class SimpleClientAdapter(JSONAdapterMixin, TapiocaAdapter):
    serializer_class = None
    api_root = "https://api.example.org"
    resource_mapping = RESOURCE_MAPPING

    def get_api_root(self, api_params, **kwargs):
        if kwargs.get("resource_name") == "another_root":
            return "https://api.another.com/"
        else:
            return self.api_root

    def get_iterator_list(self, data, **kwargs):
        return data["data"]

    def get_iterator_next_request_kwargs(
        self, request_kwargs, data, response, **kwargs
    ):
        paging = data.get("paging")
        if not paging:
            return
        url = paging.get("next")

        if url:
            return {"url": url}


SimpleClient = generate_wrapper_from_adapter(SimpleClientAdapter)


class NoneSemaphoreClientAdapter(SimpleClientAdapter):
    semaphore = None


NoneSemaphoreClient = generate_wrapper_from_adapter(NoneSemaphoreClientAdapter)


class CustomSerializer(SimpleSerializer):
    def to_kwargs(self, data, **kwargs):
        return kwargs


class SerializerClientAdapter(SimpleClientAdapter):
    serializer_class = CustomSerializer


SerializerClient = generate_wrapper_from_adapter(SerializerClientAdapter)


class XMLClientAdapter(XMLAdapterMixin, TapiocaAdapter):
    api_root = "https://api.example.org"
    resource_mapping = RESOURCE_MAPPING


XMLClient = generate_wrapper_from_adapter(XMLClientAdapter)


class RetryRequestClientAdapter(SimpleClientAdapter):
    def retry_request(self, tapioca_exception, error_message, repeat_number, **kwargs):
        if tapioca_exception.status == 400 and repeat_number <= 11:
            return True
        return False


RetryRequestClient = generate_wrapper_from_adapter(RetryRequestClientAdapter)


"""
refresh token
"""


class TokenRefreshClientAdapter(SimpleClientAdapter):
    def is_authentication_expired(self, exception, *args, **kwargs):
        return exception.status == 401

    def refresh_authentication(self, api_params, *args, **kwargs):
        new_token = "new_token"
        api_params["token"] = new_token
        return new_token


TokenRefreshClient = generate_wrapper_from_adapter(TokenRefreshClientAdapter)


class TokenRefreshByDefaultClientAdapter(TokenRefreshClientAdapter):
    refresh_token = True


TokenRefreshByDefaultClient = generate_wrapper_from_adapter(
    TokenRefreshByDefaultClientAdapter
)


class FailTokenRefreshClientAdapter(TokenRefreshByDefaultClientAdapter):
    def refresh_authentication(self, api_params, *args, **kwargs):
        return None


FailTokenRefreshClient = generate_wrapper_from_adapter(FailTokenRefreshClientAdapter)


"""
Pydantic
"""


class PydanticDefaultClientAdapter(PydanticMixin, TapiocaAdapter):
    api_root = "https://api.example.org"
    resource_mapping = {
        "test": {**test, "pydantic_model": CustomModel},
        "test_root": {**test, "pydantic_model": RootModel},
        "test_dataclass": {**test, "pydantic_model": CustomModelDT},
        "test_dataclass_root": {**test, "pydantic_model": RootModelDT},
        "test_not_found": {**test, "pydantic_model": None},
        "test_bad_pydantic_model": {**test, "pydantic_model": 100500},
        "test_bad_dataclass_model": {**test, "pydantic_model": BadModelDT},
        }


PydanticDefaultClient = generate_wrapper_from_adapter(PydanticDefaultClientAdapter)


class PydanticAllDisabledClientAdapter(PydanticDefaultClientAdapter):
    extract_root = False
    convert_to_dict = False


PydanticAllDisabledClient = generate_wrapper_from_adapter(PydanticAllDisabledClientAdapter)


class PydanticExtractRootClientAdapter(PydanticDefaultClientAdapter):
    extract_root = True
    convert_to_dict = False


PydanticExtractRootClient = generate_wrapper_from_adapter(PydanticExtractRootClientAdapter)


class PydanticConvertToDictClientAdapter(PydanticDefaultClientAdapter):
    extract_root = False
    convert_to_dict = True


PydanticConvertToDictClient = generate_wrapper_from_adapter(PydanticConvertToDictClientAdapter)


class PydanticAllEnabledClientAdapter(PydanticDefaultClientAdapter):
    extract_root = True
    convert_to_dict = True


PydanticAllEnabledClient = generate_wrapper_from_adapter(PydanticAllEnabledClientAdapter)
