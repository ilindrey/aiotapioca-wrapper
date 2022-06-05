from collections.abc import Mapping
from dataclasses import asdict, is_dataclass

import xmltodict
from orjson import JSONDecodeError, dumps, loads
from pydantic import BaseModel


class TapiocaAdapterFormMixin:
    def format_data_to_request(self, data, *args, **kwargs):
        return data

    async def response_to_native(self, response, **kwargs):
        return {"text": await response.text()}


class TapiocaAdapterJSONMixin:
    def get_request_kwargs(self, *args, **kwargs):
        request_kwargs = kwargs.get("request_kwargs", {})
        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        request_kwargs["headers"]["Content-Type"] = "application/json"
        return request_kwargs

    def format_data_to_request(self, data, *args, **kwargs):
        if data:
            return dumps(data)

    async def response_to_native(self, response, **kwargs):
        text = await response.text()
        if not text:
            return None
        try:
            return loads(text)
        except JSONDecodeError:
            return text

    def get_error_message(self, data, response, **kwargs):
        if isinstance(data, dict):
            if "error" in data:
                return data["error"]
            elif "errors" in data:
                return data["errors"]
            return str(data)
        return data


class TapiocaAdapterPydanticMixin(TapiocaAdapterJSONMixin):
    forced_to_have_model = False
    validate_data_received = True
    validate_data_sending = True
    extract_root = True
    convert_to_dict = False

    def format_data_to_request(self, data, *args, **kwargs):
        if data:
            if self.validate_data_sending and (
                not isinstance(data, BaseModel) or not is_dataclass(data)
            ):
                data = self.convert_data_to_pydantic_model("request", data, **kwargs)
            if isinstance(data, BaseModel):
                return dumps(data.dict())
            elif is_dataclass(data):
                return dumps(asdict(data))
            return dumps(data)

    async def response_to_native(self, response, **kwargs):
        data = await super().response_to_native(response, **kwargs)
        if isinstance(data, str):
            return data
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


class TapiocaAdapterXMLMixin:
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
        request_kwargs = kwargs.get("request_kwargs", {})

        # stores kwargs prefixed with 'xmltodict_unparse__' for use by xmltodict.unparse
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

        if "headers" not in request_kwargs:
            request_kwargs["headers"] = {}
        request_kwargs["headers"]["Content-Type"] = "application/xml"

        return request_kwargs

    def format_data_to_request(self, data, *args, **kwargs):
        if data:
            return self._input_branches_to_xml_bytestring(data)

    async def response_to_native(self, response, **kwargs):
        if response:
            text = await response.text()
            if "xml" in response.headers["content-type"]:
                return xmltodict.parse(text, **self._xmltodict_parse_kwargs)
            return text