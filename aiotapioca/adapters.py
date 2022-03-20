import json
import xmltodict
from aiohttp.client_exceptions import ContentTypeError
from collections.abc import Mapping

from .tapioca import TapiocaInstantiator
from .exceptions import ResponseProcessException, ClientError, ServerError
from .serializers import SimpleSerializer


def generate_wrapper_from_adapter(adapter_class):
    return TapiocaInstantiator(adapter_class)


class TapiocaAdapter:
    serializer_class = SimpleSerializer

    def __init__(self, serializer_class=None, *args, **kwargs):
        if serializer_class:
            self.serializer = serializer_class()
        else:
            self.serializer = self.get_serializer()

    def _get_to_native_method(self, method_name, value):
        if not self.serializer:
            raise NotImplementedError("This client does not have a serializer")

        def to_native_wrapper(**kwargs):
            return self._value_to_native(method_name, value, **kwargs)

        return to_native_wrapper

    def _value_to_native(self, method_name, value, **kwargs):
        return self.serializer.deserialize(method_name, value, **kwargs)

    def get_serializer(self):
        if self.serializer_class:
            return self.serializer_class()

    def get_api_root(self, api_params, **kwargs):
        return self.api_root

    def fill_resource_template_url(self, template, params):
        return template.format(**params)

    def get_request_kwargs(self, api_params, *args, **kwargs):
        serialized = self.serialize_data(kwargs.get("data"))

        kwargs.update(
            {
                "data": self.format_data_to_request(serialized),
            }
        )
        return kwargs

    def get_error_message(self, data, response=None):
        return str(data)

    async def process_response(self, response):
        if 500 <= response.status < 600:
            raise ResponseProcessException(ServerError, None)

        data = await self.response_to_native(response)

        if 400 <= response.status < 500:
            raise ResponseProcessException(ClientError, data)

        return data

    def serialize_data(self, data):
        if self.serializer:
            return self.serializer.serialize(data)
        return data

    def format_data_to_request(self, data):
        raise NotImplementedError()

    def response_to_native(self, response):
        raise NotImplementedError()

    def get_iterator_list(self, response_data):
        raise NotImplementedError()

    def get_iterator_next_request_kwargs(
        self, iterator_request_kwargs, response_data, response
    ):
        raise NotImplementedError()

    def is_authentication_expired(self, exception, *args, **kwargs):
        return False

    def refresh_authentication(self, api_params, *args, **kwargs):
        raise NotImplementedError()


class FormAdapterMixin:
    def format_data_to_request(self, data):
        return data

    async def response_to_native(self, response):
        return {"text": await response.text()}


class JSONAdapterMixin:
    def get_request_kwargs(self, api_params, *args, **kwargs):
        arguments = super().get_request_kwargs(api_params, *args, **kwargs)
        if "headers" not in arguments:
            arguments["headers"] = {}
        arguments["headers"]["Content-Type"] = "application/json"
        return arguments

    def format_data_to_request(self, data):
        if data:
            return json.dumps(data)

    async def response_to_native(self, response):
        try:
            return await response.json()
        except ContentTypeError:
            text = await response.text()
            return json.loads(text)

    async def get_error_message(self, data, response=None):
        if not data and response:
            data = await self.response_to_native(response)

        if data:
            if "error" in data:
                return data.get("error", None)
            elif "errors" in data:
                return data.get("errors")

        return data


class XMLAdapterMixin:
    def _input_branches_to_xml_bytestring(self, data):
        if isinstance(data, Mapping):
            return xmltodict.unparse(data, **self._xmltodict_unparse_kwargs).encode(
                "utf-8"
            )
        try:
            return data.encode("utf-8")
        except Exception as e:
            raise type(e)(
                "Format not recognized, please enter an XML as string or a dictionary"
                "in xmltodict spec: \n%s" % e.message
            )

    def get_request_kwargs(self, api_params, *args, **kwargs):
        # stores kwargs prefixed with 'xmltodict_unparse__' for use by xmltodict.unparse
        self._xmltodict_unparse_kwargs = {
            k[len("xmltodict_unparse__") :]: kwargs.pop(k)
            for k in kwargs.copy().keys()
            if k.startswith("xmltodict_unparse__")
        }
        # stores kwargs prefixed with 'xmltodict_parse__' for use by xmltodict.parse
        self._xmltodict_parse_kwargs = {
            k[len("xmltodict_parse__") :]: kwargs.pop(k)
            for k in kwargs.copy().keys()
            if k.startswith("xmltodict_parse__")
        }

        arguments = super().get_request_kwargs(api_params, *args, **kwargs)

        if "headers" not in arguments:
            arguments["headers"] = {}
        arguments["headers"]["Content-Type"] = "application/xml"
        return arguments

    def format_data_to_request(self, data):
        if data:
            return self._input_branches_to_xml_bytestring(data)

    async def response_to_native(self, response):
        if response:
            text = await response.text()
            if "xml" in response.headers["content-type"]:
                return xmltodict.parse(text, **self._xmltodict_parse_kwargs)
            return {"text": text}
