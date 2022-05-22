from aiotapioca import (
    JSONAdapterMixin,
    PydanticAdapterMixin,
    SimpleSerializer,
    TapiocaAdapter,
    XMLAdapterMixin,
    generate_wrapper_from_adapter,
)

from .models import (
    BadModelDT,
    CustomModel,
    CustomModelDT,
    Detail,
    DetailDT,
    RootModel,
    RootModelDT,
)
from .parsers import FooParser, foo_parser

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
    def retry_request(self, exception, *args, **kwargs):
        if kwargs["response"].status == 400 and kwargs['repeat_number'] <= 10:
            return True
        return False


RetryRequestClient = generate_wrapper_from_adapter(RetryRequestClientAdapter)


# refresh token


class TokenRefreshClientAdapter(SimpleClientAdapter):
    def is_authentication_expired(self, exception, *args, **kwargs):
        return kwargs["response"].status == 401

    def refresh_authentication(self, exception, *args, **kwargs):
        new_token = "new_token"
        kwargs['api_params']["token"] = new_token
        return new_token


TokenRefreshClient = generate_wrapper_from_adapter(TokenRefreshClientAdapter)


class TokenRefreshByDefaultClientAdapter(TokenRefreshClientAdapter):
    refresh_token = True


TokenRefreshByDefaultClient = generate_wrapper_from_adapter(
    TokenRefreshByDefaultClientAdapter
)


class FailTokenRefreshClientAdapter(TokenRefreshByDefaultClientAdapter):
    def refresh_authentication(self, exceptions, *args, **kwargs):
        return None


FailTokenRefreshClient = generate_wrapper_from_adapter(FailTokenRefreshClientAdapter)


# parsers


class FuncParserClientAdapter(SimpleClientAdapter):
    def get_resource_mapping(self, api_params, **kwargs):
        resource_mapping = super().get_resource_mapping(api_params, **kwargs)
        resource_mapping["test"]["parsers"] = foo_parser
        return resource_mapping


FuncParserClient = generate_wrapper_from_adapter(FuncParserClientAdapter)


class StaticMethodParserClientAdapter(SimpleClientAdapter):
    def get_resource_mapping(self, api_params, **kwargs):
        resource_mapping = super().get_resource_mapping(api_params, **kwargs)
        resource_mapping["test"]["parsers"] = FooParser.foo
        return resource_mapping


StaticMethodParserClient = generate_wrapper_from_adapter(
    StaticMethodParserClientAdapter
)


class ClassParserClientAdapter(SimpleClientAdapter):
    def get_resource_mapping(self, api_params, **kwargs):
        resource_mapping = super().get_resource_mapping(api_params, **kwargs)
        resource_mapping["test"]["parsers"] = FooParser
        return resource_mapping


ClassParserClient = generate_wrapper_from_adapter(ClassParserClientAdapter)


class DictParserClientAdapter(SimpleClientAdapter):
    def get_resource_mapping(self, api_params, **kwargs):
        resource_mapping = super().get_resource_mapping(api_params, **kwargs)
        resource_mapping["test"]["parsers"] = {
            "func_parser": foo_parser,
            "static_method_parser": FooParser.foo,
            "class_parser": FooParser,
        }
        return resource_mapping


DictParserClient = generate_wrapper_from_adapter(DictParserClientAdapter)


# pydantic


class PydanticDefaultClientAdapter(PydanticAdapterMixin, TapiocaAdapter):
    api_root = "https://api.example.org"
    resource_mapping = {
        "test": {
            **test,
            "pydantic_models": {
                "request": CustomModel,
                "response": {CustomModel: "GET"},
            },
        },
        "test_root": {
            **test,
            "pydantic_models": {
                "request": {Detail: ["POST"]},
                "response": {RootModel: "GET"},
            },
        },
        "test_dataclass": {
            **test,
            "pydantic_models": {
                "request": CustomModelDT,
                "response": {CustomModelDT: ["GET"]},
            },
        },
        "test_dataclass_root": {
            **test,
            "pydantic_models": {
                "request": {DetailDT: "POST"},
                "response": {RootModelDT: "GET"},
            },
        },
    }


PydanticDefaultClient = generate_wrapper_from_adapter(PydanticDefaultClientAdapter)


class PydanticForcedClientAdapter(PydanticDefaultClientAdapter):
    forced_to_have_model = True
    resource_mapping = {
        "test_not_found": {**test, "pydantic_models": None},
        "test_bad_pydantic_model": {**test, "pydantic_models": 100500},
        "test_bad_dataclass_model": {**test, "pydantic_models": BadModelDT},
    }


PydanticForcedClient = generate_wrapper_from_adapter(PydanticForcedClientAdapter)
