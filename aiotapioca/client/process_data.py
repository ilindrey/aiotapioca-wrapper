import re
import webbrowser
from collections import OrderedDict
from functools import partial
from inspect import isclass, isfunction, ismethod

from orjson import dumps

__all__ = ("ProcessData",)


class ProcessData:
    def __init__(self, api, data, resource):
        self._api = api
        self._data = data
        self._resource = resource

    def __call__(self, *args, **kwargs):
        return self._data

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data

    def __dir__(self):
        methods = [m for m in type(self).__dict__.keys() if not m.startswith("_")]
        parsers = self._resource.get("parsers")
        if parsers:
            methods += [m for m in parsers if isinstance(parsers, dict)]
            methods += [m.__name__ for m in parsers if not isinstance(parsers, dict)]
        methods += [m for m in dir(self._api.serializer) if m.startswith("to_")]
        return methods

    def __str__(self):
        if type(self._data) == OrderedDict:
            return f"<{type(self).__name__} object, printing as dict:\n{dumps(self._data).decode('utf-8')}>"
        else:
            from pprint import PrettyPrinter

            pp = PrettyPrinter(indent=4)
            return f"<{type(self).__name__} object:\n{pp.pformat(self._data)}>"

    def __getattr__(self, name):
        # Fix to be pickle-able:
        # return None for all unimplemented dunder methods
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        result = self._get_parser_from_resource(name)
        if result is not None:
            return result
        result = self._get_client_from_name_or_fallback(name)
        if result is not None:
            return result
        if name.startswith("to_"):  # deserializing
            method = self._resource.get(name)
            kwargs = method.get("params", {}) if method else {}
            return self._api.get_to_native_method(name, self._data, **kwargs)
        if name in self._data:
            return self._create(self._api, self._data, self._resource, name)
        raise AttributeError(name)

    def __getitem__(self, key):
        result = self._get_client_from_name_or_fallback(key)
        if result is None:
            raise KeyError(key)
        return result

    def open_in_browser(self):
        new = 2  # open in new tab
        webbrowser.open(self._data, new=new)

    @classmethod
    def _create(cls, api, data, resource, name=None):
        if name is not None:
            return cls(api, data[name], resource)
        return cls(api, data, resource)

    def _to_camel_case(self, name):
        """
        Convert a snake_case string in CamelCase.
        http://stackoverflow.com/questions/19053707/convert-snake-case-snake-case-to-lower-camel-case-lowercamelcase
        -in-python
        """
        if isinstance(name, int):
            return name
        components = name.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    def _to_snake_case(self, name):
        """
        Convert to snake_case.
        http://stackoverflow.com/questions/19053707/convert-snake-case-snake-case-to-lower-camel-case-lowercamelcase
        -in-python
        """
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    def _get_client_from_name_or_fallback(self, name):
        client = self._get_client_from_name(name)
        if client is not None:
            return client

        camel_case_name = self._to_camel_case(name)
        client = self._get_client_from_name(camel_case_name)
        if client is not None:
            return client

        normal_camel_case_name = camel_case_name[0].upper()
        normal_camel_case_name += camel_case_name[1:]

        client = self._get_client_from_name(normal_camel_case_name)
        if client is not None:
            return client

        return None

    def _get_client_from_name(self, name):
        if (
            isinstance(self._data, list)
            and isinstance(name, int)
            or hasattr(self._data, "__iter__")
            and name in self._data
        ):
            return self._create(self._api, self._data, self._resource, name)

        return None

    def _get_parser_from_resource(self, name, parser=None):
        if self._resource is None:
            return None

        parsers = parser or self._resource.get("parsers")
        if parsers is None:
            return None
        elif isfunction(parsers) and name == parsers.__name__:
            return partial(parsers, self._data)
        elif ismethod(parsers) and hasattr(parsers, "__self__"):
            return partial(parsers, self._data)
        elif isclass(parsers) and name == self._to_snake_case(parsers.__name__):
            parsers.data = self._data
            return parsers
        elif isinstance(parsers, dict) and name in parsers:
            parser = parsers[name]
            parser_name = (
                self._to_snake_case(parser.__name__)
                if isclass(parser)
                else parser.__name__
            )
            return self._get_parser_from_resource(parser_name, parser)

        return None
