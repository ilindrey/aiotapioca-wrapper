import re
import webbrowser
from asyncio import Semaphore, gather, run as asyncio_run
from collections import OrderedDict
from copy import copy
from functools import partial
from inspect import isclass, isfunction, iscoroutinefunction

from aiohttp import ClientSession
from orjson import dumps

from .exceptions import ResponseProcessException, TapiocaException


class TapiocaInstantiator:
    def __init__(self, adapter_class, session=None):
        self.adapter_class = adapter_class
        self._session = session

    def __call__(self, serializer_class=None, session=None, **kwargs):
        return TapiocaClient(
            self.adapter_class(serializer_class=serializer_class),
            api_params=kwargs,
            session=session or self._session,
        )


class TapiocaClient:
    def __init__(self, api, api_params=None, session=None, *args, **kwargs):
        self._api = api
        self._api_params = api_params or {}
        self._session = session

    def __str__(self):
        return f"<{type(self).__name__} object>"

    def __dir__(self):
        resource_mapping = self._api.get_resource_mapping(self._api_params)
        if self._api and self._data is None:
            return [key for key in resource_mapping.keys()]
        return []

    async def __aenter__(self):
        if self._session is None:
            self._session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self._session is not None:
            await self._session.close()

    def __getattr__(self, name):
        # Fix to be pickle-able:
        # return None for all unimplemented dunder methods
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        result = self._get_client_resource_from_name_or_fallback(name)
        if result is None:
            raise AttributeError(name)
        return result

    # def __del__(self):
    #     asyncio_run(self._close_session())

    async def _init_session(self):
        if self._session is None:
            self._session = ClientSession()
        return self._session

    async def _close_session(self):
        if self._session is not None:
            await self._session.close()

    def _get_context(self, **kwargs):
        context = {
            'client': self,
            'api': self._api,
            'api_params': self._api_params,
            'session': self._session,
        }
        context.update(kwargs)
        return context

    def _get_client_resource_from_name_or_fallback(self, name):

        # if could not access, falback to resource mapping
        resource_mapping = self._api.get_resource_mapping(self._api_params)
        if name in resource_mapping:
            resource = resource_mapping[name]
            api_root = self._api.get_api_root(self._api_params, resource_name=name)
            path = api_root.rstrip("/") + "/" + resource["resource"].lstrip("/")
            return self._wrap_in_tapioca_resource(path=path, resource=resource, resource_name=name)

        return None

    def _wrap_in_tapioca_resource(self,  *args, **kwargs):
        context = self._get_context(**kwargs)
        return TapiocaClientResource(*args, **context)

    def _repr_pretty_(self, p, cycle):
        p.text(self.__str__())


class TapiocaClientResource(TapiocaClient):
    def __init__(self, path=None, resource=None, resource_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._path = path
        self._resource = resource
        self._resource_name = resource_name

    def __str__(self):
        return f"<{type(self).__name__} object: {self._url}>"

    def __contains__(self, key):
        return key in self._resource

    def __dir__(self):
        if self._resource_name is not None:
            return [self._resource_name]
        return []

    def __call__(self, *args, **kwargs):
        path = self._path

        url_params = self._api_params.get("default_url_params", {})
        url_params.update(kwargs)
        if self._resource and url_params:
            path = self._api.fill_resource_template_url(template=path, url_params=url_params, *args, **kwargs)

        return self._wrap_in_tapioca_executor(path=path)

    def _get_doc(self):
        docs = (
            "Automatic generated __doc__ from resource_mapping.\n"
            "Resource: %s\n"
            "Docs: %s\n" % (self._resource.get("resource", ""), self._resource.get("docs", ""))
        )
        for key, value in sorted(resource.items()):
            docs += "%s: %s\n" % (key.title(), value)
        docs = docs.strip()
        return docs

    __doc__ = property(_get_doc)

    def open_docs(self):
        if not self._resource:
            raise KeyError()

        new = 2  # open in new tab
        webbrowser.open(self._resource["docs"], new=new)

    def open_in_browser(self):
        new = 2  # open in new tab
        webbrowser.open(self._data, new=new)

    def _get_context(self, **kwargs):
        context = super()._get_context(**kwargs)
        context.update({
            'path': self._path,
            'resource': self._resource,
            'resource_name': self._resource_name,
            **kwargs
            })
        return context

    def _wrap_in_tapioca_executor(self, *args, **kwargs):
        context = self._get_context(**kwargs)
        return TapiocaClientExecutor(*args, **context)


class TapiocaClientExecutor(TapiocaClientResource):
    def __init__(self, response=None, data=None, request_kwargs=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._response = response
        self._data = data
        self._request_kwargs = request_kwargs or {}

    def __str__(self):
        if type(self._data) is OrderedDict:
            return f"<{type(self).__name__} object, printing as dict: {dumps(self._data, indent=4).decode('utf-8')}>"
        else:
            from pprint import PrettyPrinter
            pp = PrettyPrinter(indent=4)
            return f"<{type(self).__name__} object: {pp.pformat(self._data)}>"

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        raise TapiocaException(
            "This operation cannot be done on a TapiocaClientExecutor object."
        )

    def __iter__(self):
        raise TapiocaException("Cannot iterate over a TapiocaClientExecutor object.")

    def __call__(self, *args, **kwargs):
        # return self._wrap_in_tapioca_response(data=self._data.__call__(*args, **kwargs))
        return self._wrap_in_tapioca_response()

    def __dir__(self):
        methods = [
            m for m in type(self).__dict__.keys() if not m.startswith("_")
        ]
        return methods

    async def get(self, *args, **kwargs):
        return await self._send("GET", *args, **kwargs)

    async def post(self, *args, **kwargs):
        return await self._send("POST", *args, **kwargs)

    async def options(self, *args, **kwargs):
        return await self._send("OPTIONS", *args, **kwargs)

    async def put(self, *args, **kwargs):
        return await self._send("PUT", *args, **kwargs)

    async def patch(self, *args, **kwargs):
        return await self._send("PATCH", *args, **kwargs)

    async def delete(self, *args, **kwargs):
        return await self._send("DELETE", *args, **kwargs)

    async def post_batch(self, *args, **kwargs):
        return await self._send_batch("POST", *args, **kwargs)

    async def put_batch(self, *args, **kwargs):
        return await self._send_batch("PUT", *args, **kwargs)

    async def patch_batch(self, *args, **kwargs):
        return await self._send_batch("PATCH", *args, **kwargs)

    async def delete_batch(self, *args, **kwargs):
        return await self._send_batch("DELETE", *args, **kwargs)

    async def pages(self, max_pages=None, max_items=None):
        executor = self
        iterator_list = executor._get_iterator_list()
        page_count = 0
        item_count = 0

        while iterator_list:
            for item in iterator_list:
                if executor._reached_max_limits(
                    page_count, item_count, max_pages, max_items
                ):
                    break
                yield executor._wrap_in_tapioca(item)
                item_count += 1

            page_count += 1

            if executor._reached_max_limits(
                page_count, item_count, max_pages, max_items
            ):
                break

            next_request_kwargs = await executor._get_iterator_next_request_kwargs()

            if not next_request_kwargs:
                break

            response = await executor.get(**next_request_kwargs)
            executor = response()
            iterator_list = executor._get_iterator_list()

    async def _send_batch(self, request_method, *args, **kwargs):

        data = kwargs.pop("data", [])

        kwargs["semaphore_class"] = Semaphore(self._get_semaphore_value(kwargs))

        results = await gather(
            *[
                self._send(request_method, *args, **{**kwargs, "data": row})
                for row in data
            ]
        )

        return results

    async def _send(self, request_method, *args, **kwargs):

        if "semaphore_class" not in kwargs:
            kwargs["semaphore_class"] = Semaphore(self._get_semaphore_value(kwargs))

        semaphore = kwargs.pop("semaphore_class", Semaphore())

        refresh_token = (
            kwargs.pop("refresh_token", False) is True
            or self._api_params.get("refresh_token") is True
            or self._api.refresh_token is True
            or False
        )
        repeat_number = 0

        async with semaphore:
            response = await self._make_request(
                request_method, refresh_token, repeat_number, *args, **kwargs
            )

        return response

    def _get_semaphore_value(self, kwargs):
        semaphore = (
            kwargs.pop("semaphore", None)
            or self._api_params.get("semaphore")
            or self._api.semaphore
        )
        return semaphore

    async def _make_request(
        self, request_method, refresh_token=False, repeat_number=0, *args, **kwargs
    ):
        if "url" not in kwargs:
            kwargs["url"] = self._path

        request_kwargs = self._request_kwargs or kwargs

        context = self._get_context(
            request_method=request_method,
            refresh_token=refresh_token,
            repeat_number=repeat_number,
            request_kwargs={**request_kwargs},
        )
        del context["client"]
        del context["data"]

        data = None
        request_kwargs = context["request_kwargs"]
        response = context["response"]

        try:
            request_kwargs = self._api.get_request_kwargs(*args, **context)
            response = await self._session.request(request_method, **request_kwargs)
            context.update({"response": response, "request_kwargs": request_kwargs})
            data = await self._coro_wrap(self._api.process_response, **context)
            context["data"] = data
        except ResponseProcessException as ex:

            repeat_number += 1

            client = self._wrap_in_tapioca_executor(
                data=ex.data, response=response, request_kwargs=request_kwargs
            )

            context.update(
                {
                    "client": client,
                    "response": response,
                    "request_kwargs": request_kwargs,
                    "repeat_number": repeat_number,
                    "data": ex.data,
                }
            )

            if repeat_number > self._api.max_retries_requests:
                await self._coro_wrap(self._api.error_handling, ex, **context)

            propagate_exception = True

            auth_expired = await self._coro_wrap(
                self._api.is_authentication_expired, ex, **context
            )
            if refresh_token and auth_expired:
                self._refresh_data = await self._coro_wrap(
                    self._api.refresh_authentication, ex, **context
                )
                if self._refresh_data:
                    propagate_exception = False
                    return await self._make_request(
                        request_method,
                        refresh_token=False,
                        repeat_number=repeat_number,
                        *args,
                        **kwargs
                    )

            if await self._coro_wrap(self._api.retry_request, ex, **context):
                propagate_exception = False
                return await self._make_request(
                    request_method,
                    refresh_token=False,
                    repeat_number=repeat_number,
                    *args,
                    **kwargs
                )

            if propagate_exception:
                await self._coro_wrap(self._api.error_handling, ex, **context)

        except Exception as ex:
            await self._coro_wrap(self._api.error_handling, ex, *args, **context)

        return self._wrap_in_tapioca_executor(
            data=data, response=response, request_kwargs=request_kwargs
        )

    @staticmethod
    def _reached_max_limits(page_count, item_count, max_pages, max_items):
        reached_page_limit = max_pages is not None and max_pages <= page_count
        reached_item_limit = max_items is not None and max_items <= item_count
        return reached_page_limit or reached_item_limit

    def _get_iterator_list(self):
        return self._api.get_iterator_list(**self._context())

    async def _get_iterator_next_request_kwargs(self):
        return await self._coro_wrap(
            self._api.get_iterator_next_request_kwargs, **self._context()
        )

    @staticmethod
    async def _coro_wrap(func, *args, **kwargs):
        if iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        return result

    def _get_context(self, **kwargs):
        context = super()._get_context(**kwargs)
        context.update({
            'response': self._response,
            'data': self._data,
            'request_kwargs': self._request_kwargs,
            **kwargs,
            })
        return context

    def _wrap_in_tapioca_response(self, *args, **kwargs):
        context = self._get_context(**kwargs)
        return TapiocaClientResponse(*args, **context)


class TapiocaClientResponse(TapiocaClientExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
            return self._api._get_to_native_method(name, self._data, **kwargs)
        return self._wrap_in_tapioca_response(getattr(self._data, name))

    def __getitem__(self, key):
        result = self._get_client_from_name_or_fallback(key)
        if result is None:
            raise KeyError(key)
        return result

    def __dir__(self):
        methods = [
            m for m in type(self).__dict__.keys() if not m.startswith("_")
        ]
        parsers = self._resource.get("parsers")
        if parsers:
            methods += [m for m in parsers if isinstance(parsers, dict)]
            methods += [m.__name__ for m in parsers if not isinstance(parsers, dict)]
        methods += [m for m in dir(self._api.serializer) if m.startswith("to_")]
        return methods

    def __contains__(self, key):
        return key in self._data

    @property
    def path(self):
        return self._path

    @property
    def data(self):
        return self._data

    @property
    def response(self):
        if self._response is None:
            raise TapiocaException("This instance has no response object.")
        return self._response

    @property
    def status(self):
        return self.response.status

    @property
    def url(self):
        return self.response.url

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
            return self._wrap_in_tapioca(data=self._data[name])

        return None

    def _get_parser_from_resource(self, name, parser=None):
        if self._resource is None:
            return None

        parsers = parser or self._resource.get("parsers")
        if parsers is None:
            return None
        elif isfunction(parsers) and name == parsers.__name__:
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
