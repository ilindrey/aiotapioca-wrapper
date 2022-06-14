from asyncio import to_thread

from aiotapioca.exceptions import ClientError, ServerError
from aiotapioca.serializers import SimpleSerializer

from ..utils import coro_wrap
from .mixins import (
    TapiocaAdapterFormMixin,
    TapiocaAdapterJSONMixin,
    TapiocaAdapterPydanticMixin,
    TapiocaAdapterXMLMixin,
)

__all__ = (
    "TapiocaAdapter",
    "TapiocaAdapterForm",
    "TapiocaAdapterJSON",
    "TapiocaAdapterPydantic",
    "TapiocaAdapterXML",
)


class TapiocaAdapter:
    serializer_class = SimpleSerializer
    max_retries_requests = 10
    semaphore = 10
    refresh_token = False
    resource_mapping = None
    api_root = None

    def __init__(self, serializer_class=None, *args, **kwargs):
        if serializer_class:
            self.serializer = serializer_class()
        else:
            self.serializer = self.get_serializer()

    def get_api_root(self, api_params, **kwargs):
        return self.api_root or ""

    def get_resource_mapping(self, api_params, **kwargs):
        return self.resource_mapping or {}

    def get_serializer(self):
        if self.serializer_class:
            return self.serializer_class()

    def get_to_native_method(self, method_name, value, **default_kwargs):
        if not self.serializer:
            raise NotImplementedError("This client does not have a serializer")

        def to_native_wrapper(**kwargs):
            params = default_kwargs or {}
            params.update(kwargs)
            return self.value_to_native(method_name, value, **params)

        return to_native_wrapper

    def value_to_native(self, method_name, value, **kwargs):
        return self.serializer.deserialize(method_name, value, **kwargs)

    def serialize_data(self, data, *args, **kwargs):
        if self.serializer:
            return self.serializer.serialize(data)
        return data

    def fill_resource_template_url(self, template, url_params, **kwargs):
        if isinstance(template, str):
            return template.format(**url_params)
        else:
            return template

    async def prepare_request_kwargs(self, *args, **kwargs):
        request_kwargs = kwargs.get("request_kwargs", {})
        request_params = await coro_wrap(self.get_request_kwargs, *args, **kwargs)
        request_kwargs.update(request_params)
        request_kwargs["data"] = await self.data_to_request(
            request_kwargs.get("data"), *args, **kwargs
        )
        return request_kwargs

    def get_request_kwargs(self, *args, **kwargs):
        raise NotImplementedError()

    async def data_to_request(self, data, *args, **kwargs):
        if not data:
            return None
        data = await to_thread(self.prepare_request_data, data, *args, **kwargs)
        return data

    def prepare_request_data(self, data, *args, **kwargs):
        serialized = self.serialize_data(data, *args, **kwargs)
        return self.format_data_to_request(serialized, *args, **kwargs)

    def format_data_to_request(self, data, *args, **kwargs):
        raise NotImplementedError()

    async def process_response(self, response, **kwargs):
        non_native_data = await self.get_response_data(response, **kwargs)
        data = await self.response_to_native(non_native_data, response, **kwargs)
        if 400 <= response.status < 600:
            message = self.get_error_message(data, response, **kwargs)
            self.raise_response_error(message, data, response, **kwargs)
        return data

    async def get_response_data(self, response, **kwargs):
        return await response.text()

    async def response_to_native(self, non_native_data, response, **kwargs):
        if not non_native_data:
            return None
        data = await to_thread(
            self.format_response_data_to_native, non_native_data, response, **kwargs
        )
        return data

    def format_response_data_to_native(self, non_native_data, response, **kwargs):
        raise NotImplementedError()

    def get_error_message(self, data, response, **kwargs):
        return str(data)

    def raise_response_error(self, message, data, response, **kwargs):
        if 400 <= response.status < 500:
            raise ClientError(message, data, response, **kwargs)
        elif 500 <= response.status < 600:
            raise ServerError(message, data, response, **kwargs)

    def get_iterator_list(self, data, **kwargs):
        raise NotImplementedError()

    def get_iterator_next_request_kwargs(
        self, request_kwargs, data, response, **kwargs
    ):
        raise NotImplementedError()

    def is_authentication_expired(self, exception, repeat_number=0, **kwargs):
        return False

    def refresh_authentication(self, exception, repeat_number=0, **kwargs):
        raise NotImplementedError()

    def retry_request(self, exception, repeat_number=0, **kwargs):
        return False

    def error_handling(self, exception, repeat_number=0, **kwargs):
        raise


class TapiocaAdapterForm(TapiocaAdapterFormMixin, TapiocaAdapter):

    pass


class TapiocaAdapterJSON(TapiocaAdapterJSONMixin, TapiocaAdapter):

    pass


class TapiocaAdapterPydantic(TapiocaAdapterPydanticMixin, TapiocaAdapter):

    pass


class TapiocaAdapterXML(TapiocaAdapterXMLMixin, TapiocaAdapter):

    pass
