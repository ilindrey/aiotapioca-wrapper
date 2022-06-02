import re
import webbrowser
from asyncio import Semaphore, gather, get_event_loop
from collections import OrderedDict
from copy import copy
from functools import partial
from inspect import isclass, iscoroutinefunction, isfunction

from aiohttp import ClientSession
from orjson import dumps

from aiotapioca.exceptions import ResponseProcessException, TapiocaException

from .base import (
    BaseTapiocaClient,
    BaseTapiocaExecutorClient,
    BaseTapiocaResourceClient,
    BaseTapiocaResponseClient,
)


class TapiocaClient(BaseTapiocaClient):
    def __dir__(self):
        resource_mapping = self._api.get_resource_mapping(self._api_params)
        if self._api and self._data is None:
            return [key for key in resource_mapping.keys()]
        return []

    def __getattr__(self, name):
        # Fix to be pickle-able:
        # return None for all unimplemented dunder methods
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        result = self._get_client_resource_from_name_or_fallback(name)
        if result is None:
            raise AttributeError(name)
        return result

    async def __aenter__(self):
        return await self.initialize()

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    def __await__(self):
        return self.initialize().__await__()

    def __del__(self):
        try:
            if not self.closed:
                loop = get_event_loop()
                coro = self.close()
                if loop.is_running():
                    loop.create_task(coro)
                else:
                    loop.run_until_complete(coro)
        except Exception:
            pass

    async def close(self):
        if not self.closed:
            await self._session.close()

    def _get_client_resource_from_name_or_fallback(self, name):

        # if could not access, falback to resource mapping
        resource_mapping = self._api.get_resource_mapping(self._api_params)
        if name in resource_mapping:
            resource = resource_mapping[name]
            api_root = self._api.get_api_root(self._api_params, resource_name=name)
            path = api_root.rstrip("/") + "/" + resource["resource"].lstrip("/")
            return self._wrap_in_tapioca_resource(
                path=path, resource=resource, resource_name=name
            )

        return None

    def _get_context(self, **kwargs):
        context = super()._get_context(**kwargs)
        context['client'] = self
        return context


class TapiocaClientResource(BaseTapiocaResourceClient):
    def __str__(self):
        return f"<{type(self).__name__} object: {self._resource['resource']}>"

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
            path = self._api.fill_resource_template_url(
                template=path, url_params=url_params, *args, **kwargs
            )

        return self._wrap_in_tapioca_executor(path=path)

    def _get_doc(self):
        resource = copy(self._resource or {})
        docs = (
            "Automatic generated __doc__ from resource_mapping.\n"
            "Resource: %s\n"
            "Docs: %s\n"
            % (resource.pop("resource", ""), resource.pop("docs", ""))
        )
        for key, value in sorted(resource.items()):
            docs += "%s: %s\n" % (key.title(), value)
        docs = docs.strip()
        return docs

    __doc__ = property(_get_doc)

    def open_docs(self):
        if not self._resource:
            raise ValueError()

        new = 2  # open in new tab
        webbrowser.open(self._resource["docs"], new=new)

    def open_in_browser(self):
        new = 2  # open in new tab
        webbrowser.open(self._data, new=new)


class TapiocaClientExecutor(BaseTapiocaExecutorClient):
    def __str__(self):
        return f"<{type(self).__name__} object: {self._response or ''}>"

    def __getitem__(self, key):
        raise TapiocaException(
            "This operation cannot be done on a TapiocaClientExecutor object."
        )

    def __iter__(self):
        raise TapiocaException("Cannot iterate over a TapiocaClientExecutor object.")

    def __dir__(self):
        methods = [m for m in type(self).__dict__.keys() if not m.startswith("_")]
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
            for _ in iterator_list:
                if executor._reached_max_limits(
                    page_count, item_count, max_pages, max_items
                ):
                    break
                yield executor._wrap_in_tapioca_response()
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
        # del context["client"]
        del context["data"]

        data = None
        request_kwargs = context["request_kwargs"]
        response = context["response"]

        try:
            await self.initialize()
            request_kwargs = self._api.get_request_kwargs(*args, **context)
            response = await self._session.request(request_method, **request_kwargs)
            context.update({"response": response, "request_kwargs": request_kwargs})
            data = await self._coro_wrap(self._api.process_response, **context)
            context["data"] = data
        except ResponseProcessException as ex:

            repeat_number += 1

            self._response = response
            self._data = getattr(ex, 'data', None)
            self._request_kwargs = request_kwargs

            context.update(
                {
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
                        **kwargs,
                    )

            if await self._coro_wrap(self._api.retry_request, ex, **context):
                propagate_exception = False
                return await self._make_request(
                    request_method,
                    refresh_token=False,
                    repeat_number=repeat_number,
                    *args,
                    **kwargs,
                )

            if propagate_exception:
                await self._coro_wrap(self._api.error_handling, ex, **context)

        except Exception as ex:
            await self._coro_wrap(self._api.error_handling, ex, *args, **context)

        return self._wrap_in_tapioca_response(data=data, response=response, request_kwargs=request_kwargs)

    @staticmethod
    def _reached_max_limits(page_count, item_count, max_pages, max_items):
        reached_page_limit = max_pages is not None and max_pages <= page_count
        reached_item_limit = max_items is not None and max_items <= item_count
        return reached_page_limit or reached_item_limit

    def _get_iterator_list(self):
        return self._api.get_iterator_list(**self._get_context())

    async def _get_iterator_next_request_kwargs(self):
        return await self._coro_wrap(
            self._api.get_iterator_next_request_kwargs, **self._get_context()
        )

    @staticmethod
    async def _coro_wrap(func, *args, **kwargs):
        if iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        return result


class TapiocaClientResponse(BaseTapiocaResponseClient):
    def __str__(self):
        if type(self._data) is OrderedDict:
            return f"<{type(self).__name__} object, printing as dict: {dumps(self._data).decode('utf-8')}>"
        else:
            from pprint import PrettyPrinter
            pp = PrettyPrinter(indent=4)
            return f"<{type(self).__name__} object: {pp.pformat(self._data)}>"

    def __call__(self, *args, **kwargs):
        return self._wrap_in_tapioca_executor()

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
        methods = [m for m in type(self).__dict__.keys() if not m.startswith("_")]
        parsers = self._resource.get("parsers")
        if parsers:
            methods += [m for m in parsers if isinstance(parsers, dict)]
            methods += [m.__name__ for m in parsers if not isinstance(parsers, dict)]
        methods += [m for m in dir(self._api.serializer) if m.startswith("to_")]
        return methods

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data

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
            return self._wrap_in_tapioca_response(data=self._data[name])

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
