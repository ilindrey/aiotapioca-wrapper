from typing import Any, Dict, Type

from aiotapioca import (
    SimpleSerializer,
    TapiocaAdapterJSON,
    generate_wrapper_from_adapter,
)
from aiotapioca.serializers import BaseSerializer

from .parsers import FooParser, foo_parser


test = {
    "resource": "test/",
    "docs": "http://www.example.org",
}

RESOURCE_MAPPING: Dict[str, Any] = {
    "test": test,
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


class SimpleClientAdapter(TapiocaAdapterJSON):
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
            return {**request_kwargs, "url": url}


SimpleClient = generate_wrapper_from_adapter(SimpleClientAdapter)


class CustomSerializer(SimpleSerializer):
    def to_kwargs(self, data, **kwargs):
        return kwargs


class SerializerClientAdapter(SimpleClientAdapter):
    serializer_class: Type[BaseSerializer] = CustomSerializer


SerializerClient = generate_wrapper_from_adapter(SerializerClientAdapter)


class RetryRequestClientAdapter(SimpleClientAdapter):
    def retry_request(self, exception, *args, **kwargs):
        return kwargs["response"].status == 400


RetryRequestClient = generate_wrapper_from_adapter(RetryRequestClientAdapter)


# refresh token


class TokenRefreshClientAdapter(SimpleClientAdapter):
    def is_authentication_expired(self, exception, *args, **kwargs):
        return kwargs["response"].status == 401

    def refresh_authentication(self, exception, *args, **kwargs):
        new_token = "new_token"
        kwargs["api_params"]["token"] = new_token
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


class ClassMethodParserClientAdapter(SimpleClientAdapter):
    def get_resource_mapping(self, api_params, **kwargs):
        resource_mapping = super().get_resource_mapping(api_params, **kwargs)
        resource_mapping["test"]["parsers"] = FooParser.spam
        return resource_mapping


ClassMethodParserClient = generate_wrapper_from_adapter(ClassMethodParserClientAdapter)


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
