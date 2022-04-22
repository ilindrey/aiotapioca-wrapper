import orjson
import xmltodict
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from pydantic import BaseModel

from .aiotapioca import TapiocaInstantiator
from .exceptions import ResponseProcessException, ClientError, ServerError
from .serializers import SimpleSerializer


def generate_wrapper_from_adapter(adapter_class):
    return TapiocaInstantiator(adapter_class)


class TapiocaAdapter:
    serializer_class = SimpleSerializer
    refresh_token = False
    semaphore = 10

    def __init__(self, serializer_class=None, *args, **kwargs):
        if serializer_class:
            self.serializer = serializer_class()
        else:
            self.serializer = self.get_serializer()

    def _get_to_native_method(self, method_name, value, **default_kwargs):
        if not self.serializer:
            raise NotImplementedError("This client does not have a serializer")

        def to_native_wrapper(**kwargs):
            params = default_kwargs or {}
            params.update(kwargs)
            return self._value_to_native(method_name, value, **params)

        return to_native_wrapper

    def _value_to_native(self, method_name, value, **kwargs):
        return self.serializer.deserialize(method_name, value, **kwargs)

    def get_serializer(self):
        if self.serializer_class:
            return self.serializer_class()

    def serialize_data(self, data, **kwargs):
        if self.serializer:
            return self.serializer.serialize(data)
        return data

    def get_api_root(self, api_params, **kwargs):
        return self.api_root

    def get_resource_mapping(self, api_params, **kwargs):
        return self.resource_mapping

    def fill_resource_template_url(self, template, url_params, **kwargs):
        if isinstance(template, str):
            return template.format(**url_params)
        else:
            return template

    def get_request_kwargs(self, *args, **kwargs):
        request_kwargs = kwargs.get("request_kwargs", {})

        serialized = self.serialize_data(request_kwargs.get("data"), **kwargs)
        request_kwargs.update(
            {
                "data": self.format_data_to_request(serialized, **kwargs),
            }
        )
        return request_kwargs

    async def process_response(self, response, **kwargs):

        if 500 <= response.status < 600:
            raise ResponseProcessException(ServerError, None)

        data = await self.response_to_native(response, **kwargs)

        if 400 <= response.status < 500:
            raise ResponseProcessException(ClientError, data)

        return data

    def get_error_message(self, data, response=None, **kwargs):
        return str(data)

    def format_data_to_request(self, data, **kwargs):
        raise NotImplementedError()

    def response_to_native(self, response, **kwargs):
        raise NotImplementedError()

    def get_iterator_list(self, data, **kwargs):
        raise NotImplementedError()

    def get_iterator_next_request_kwargs(
        self, request_kwargs, data, response, **kwargs
    ):
        raise NotImplementedError()

    def is_authentication_expired(self, exception, *args, **kwargs):
        return False

    def refresh_authentication(self, api_params, *args, **kwargs):
        raise NotImplementedError()

    def retry_request(self, tapioca_exception, error_message, repeat_number, **kwargs):
        """
        Conditions for repeating a request.
        If it returns True, the request will be repeated.
        Code based on:
        https://github.com/pavelmaksimov/tapi-wrapper/blob/262468e039db83e8e13564966ad96be39a3d2dab/tapi2/adapters.py#L218
        """
        return False

    def error_handling(self, tapioca_exception, error_message, repeat_number, **kwargs):
        """
        Wrapper for throwing custom exceptions. When,
        for example, the server responds with 200,
        and errors are passed inside json.
        Code based on:
        https://github.com/pavelmaksimov/tapi-wrapper/blob/262468e039db83e8e13564966ad96be39a3d2dab/tapi2/adapters.py#L165
        """
        raise tapioca_exception


class FormAdapterMixin:
    def format_data_to_request(self, data, **kwargs):
        return data

    async def response_to_native(self, response, **kwargs):
        return {"text": await response.text()}


class JSONAdapterMixin:
    def get_request_kwargs(self, *args, **kwargs):
        arguments = super().get_request_kwargs(*args, **kwargs)
        if "headers" not in arguments:
            arguments["headers"] = {}
        arguments["headers"]["Content-Type"] = "application/json"
        return arguments

    def format_data_to_request(self, data, **kwargs):
        if data:
            return orjson.dumps(data)

    async def response_to_native(self, response, **kwargs):
        text = await response.text()
        if text:
            return orjson.loads(text)

    async def get_error_message(self, data, response=None, **kwargs):
        if not data and response:
            data = await self.response_to_native(response, **kwargs)
        if data:
            if "error" in data:
                return data.get("error")
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

    def get_request_kwargs(self, *args, **kwargs):
        # stores kwargs prefixed with 'xmltodict_unparse__' for use by xmltodict.unparse
        request_kwargs = kwargs.get("request_kwargs", {})
        self._xmltodict_unparse_kwargs = {
            k[len("xmltodict_unparse__") :]: request_kwargs.pop(k)
            for k in request_kwargs.copy().keys()
            if k.startswith("xmltodict_unparse__")
        }
        # stores kwargs prefixed with 'xmltodict_parse__' for use by xmltodict.parse
        self._xmltodict_parse_kwargs = {
            k[len("xmltodict_parse__") :]: request_kwargs.pop(k)
            for k in request_kwargs.copy().keys()
            if k.startswith("xmltodict_parse__")
        }

        kwargs["request_kwargs"] = request_kwargs
        arguments = super().get_request_kwargs(*args, **kwargs)

        if "headers" not in arguments:
            arguments["headers"] = {}
        arguments["headers"]["Content-Type"] = "application/xml"
        return arguments

    def format_data_to_request(self, data, **kwargs):
        if data:
            return self._input_branches_to_xml_bytestring(data)

    async def response_to_native(self, response, **kwargs):
        if response:
            text = await response.text()
            if "xml" in response.headers["content-type"]:
                return xmltodict.parse(text, **self._xmltodict_parse_kwargs)
            return {"text": text}


class PydanticAdapterMixin:
    forced_to_have_model = False
    validate_data_received = True
    validate_data_sending = True
    extract_root = True
    convert_to_dict = False

    def get_request_kwargs(self, *args, **kwargs):
        arguments = super().get_request_kwargs(*args, **kwargs)
        if "headers" not in arguments:
            arguments["headers"] = {}
        arguments["headers"]["Content-Type"] = "application/json"
        return arguments

    def format_data_to_request(self, data, **kwargs):
        if data:
            if self.validate_data_sending and (
                not isinstance(data, BaseModel) or not is_dataclass(data)
            ):
                data = self.convert_data_to_pydantic_model("request", data, **kwargs)
            if isinstance(data, BaseModel):
                return orjson.dumps(data.dict())
            elif is_dataclass(data):
                return orjson.dumps(asdict(data))
            return orjson.dumps(data)

    async def response_to_native(self, response, **kwargs):
        text = await response.text()
        if text:
            data = orjson.loads(text)
            if self.validate_data_received and response.status == 200:
                data = self.convert_data_to_pydantic_model("response", data, **kwargs)
                if isinstance(data, BaseModel):
                    if self.convert_to_dict:
                        data = data.dict()
                    if self.extract_root:
                        if hasattr(data, "__root__"):
                            return data.__root__
                        elif "__root__" in data:
                            return data["__root__"]
                    return data
                return data
            return data

    def convert_data_to_pydantic_model(self, type_convert, data, **kwargs):
        model = self.get_pydantic_model(type_convert, **kwargs)
        if type(model) == type(BaseModel):
            return model.parse_obj(data)
        return data

    def get_pydantic_model(self, type_convert, resource, request_method, **kwargs):
        model = None
        models = resource.get("pydantic_models")
        if type(models) == type(BaseModel) or is_dataclass(models):
            model = models
        elif isinstance(models, dict):
            method = request_method.upper()
            if "request" in models or "response" in models:
                models = models.get(type_convert)
            if type(models) == type(BaseModel) or is_dataclass(models):
                model = models
            elif isinstance(models, dict):
                for key, value in models.items():
                    if type(key) == type(BaseModel) or is_dataclass(key):
                        if isinstance(value, str) and value.upper() == method:
                            model = key
                            break
                        elif isinstance(value, list) or isinstance(value, tuple):
                            for item in value:
                                if item.upper() == request_method:
                                    model = key
                                    break
        # search default model
        if not model and isinstance(models, dict):
            if "request" in models or "response" in models:
                models = models.get(type_convert)
            if isinstance(models, dict):
                for key, value in models.items():
                    if value is None:
                        model = key
                        break
        if self.forced_to_have_model and not model:
            raise ValueError(
                "Pydantic model not found."
                " Specify the pydantic models in the pydantic_models parameter in resource_mapping"
            )
        if is_dataclass(model):
            if hasattr(model, "__pydantic_model__"):
                model = model.__pydantic_model__
            else:
                raise TypeError(f"It isn't pydantic dataclass: {model}.")
        if self.forced_to_have_model and type(model) != type(BaseModel):
            raise TypeError(f"It isn't pydantic model: {model}.")
        return model

    async def get_error_message(self, data, response=None, **kwargs):
        if not data and response:
            data = await self.response_to_native(response, **kwargs)
        if data:
            if "error" in data:
                return data.get("error")
            elif "errors" in data:
                return data.get("errors")
        return data
