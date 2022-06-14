from collections.abc import Mapping
from dataclasses import asdict, is_dataclass

import xmltodict
from orjson import JSONDecodeError, dumps, loads
from pydantic import BaseModel, parse_obj_as

__all__ = (
    "TapiocaAdapterFormMixin",
    "TapiocaAdapterJSONMixin",
    "TapiocaAdapterPydanticMixin",
    "TapiocaAdapterXMLMixin",
)


class TapiocaAdapterFormMixin:
    def format_data_to_request(self, data, *args, **kwargs):
        return data

    def format_response_data_to_native(self, non_native_data, response, **kwargs):
        return {"text": non_native_data}


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

    def format_response_data_to_native(self, non_native_data, response, **kwargs):
        if not non_native_data:
            return None
        try:
            return loads(non_native_data)
        except JSONDecodeError:
            return non_native_data

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

    def format_response_data_to_native(self, non_native_data, response, **kwargs):
        data = super().format_response_data_to_native(
            non_native_data, response, **kwargs
        )
        if isinstance(data, str):
            return data
        if self.validate_data_received and response.status == 200:
            data = self.convert_data_to_pydantic_model("response", data, **kwargs)

            if isinstance(data, BaseModel) or is_dataclass(data):
                if self.convert_to_dict:
                    data = data.dict() if isinstance(data, BaseModel) else asdict(data)
                if self.extract_root and not is_dataclass(data):
                    if hasattr(data, "__root__"):
                        return data.__root__
                    elif "__root__" in data:
                        return data["__root__"]
                return data
            return data
        return data

    def convert_data_to_pydantic_model(self, type_convert, data, **kwargs):
        model = self.get_pydantic_model(type_convert, **kwargs)
        if model:
            return parse_obj_as(model, data)
        return data

    def get_pydantic_model(self, type_convert, resource, request_method, **kwargs):
        model = None
        models = resource.get("pydantic_models")
        if type(models) is type(BaseModel) or is_dataclass(models):
            model = models
        elif isinstance(models, dict):
            method = request_method.upper()
            if "request" in models or "response" in models:
                models = models.get(type_convert)
            if type(models) is type(BaseModel) or is_dataclass(models):
                model = models
            elif isinstance(models, dict):
                for key, value in models.items():
                    if type(key) is type(BaseModel) or is_dataclass(key):
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
        if self.forced_to_have_model:
            if not model:
                raise ValueError(
                    "Pydantic model not found."
                    " Specify the pydantic models in the pydantic_models parameter in resource_mapping"
                )
            if (
                type(model) is not type(BaseModel)
                or is_dataclass(model)
                and not hasattr(model, "__pydantic_model__")
            ):
                raise TypeError(f"It isn't pydantic model or dataclass: {model}.")
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

    def format_response_data_to_native(self, non_native_data, response, **kwargs):
        if non_native_data:
            if "xml" in response.headers["content-type"]:
                return xmltodict.parse(non_native_data, **self._xmltodict_parse_kwargs)
            return non_native_data
