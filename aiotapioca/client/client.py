import re
import webbrowser
from asyncio import Semaphore, gather, get_event_loop

from aiotapioca.exceptions import ResponseProcessException

from ..utils import coro_wrap
from .base import (
    BaseTapiocaClient,
    BaseTapiocaClientExecutor,
    BaseTapiocaClientResource,
    BaseTapiocaClientResponse,
)

__all__ = (
    "TapiocaClient",
    "TapiocaClientResource",
    "TapiocaClientExecutor",
    "TapiocaClientResponse",
)


class TapiocaClient(BaseTapiocaClient):
    def __dir__(self):
        methods = ["api_params", "close", "closed", "initialize", "session"]
        resource_mapping = self._api.get_resource_mapping(self._api_params)
        if resource_mapping:
            methods.extend([key for key in resource_mapping.keys()])
            return methods
        return methods

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

    def _get_context(self, **kwargs):
        context = super()._get_context(**kwargs)
        context["client"] = self
        return context

    def _get_client_resource_from_name_or_fallback(self, name):

        # if could not access, faдlback to resource mapping
        resource_mapping = self._api.get_resource_mapping(self._api_params)
        if name in resource_mapping:
            resource = resource_mapping[name]
            api_root = self._api.get_api_root(self._api_params, resource_name=name)
            path = api_root.rstrip("/") + "/" + resource["resource"].lstrip("/")
            return self._wrap_in_tapioca_resource(
                path=path, resource=resource, resource_name=name
            )

        return None


class TapiocaClientResource(BaseTapiocaClientResource):
    def __str__(self):
        return f"<{type(self).__name__} object: {self._resource_name}>"

    def __contains__(self, key):
        return key in self._resource

    def __dir__(self):
        methods = [
            "api_params",
            "path",
            "resource",
            "resource_name",
            "session",
            "open_docs",
        ]
        if self._resource_name is not None:
            methods.extend([self._resource_name])
            return methods
        return methods

    def __call__(self, **kwargs):
        path = self._path

        url_params = self._api_params.get("default_url_params", {})
        url_params.update(kwargs)
        if self._resource and url_params:
            path = self._api.fill_resource_template_url(
                **self._get_context(url_params=url_params, template=self._path)
            )

        return self._wrap_in_tapioca_executor(path=path)

    def _get_doc(self):
        from copy import copy

        resource = copy(self._resource or {})
        docs = (
            "Automatic generated __doc__ from resource_mapping.\n"
            f"Resource: {resource.pop('resource', '')}\n"
            f"Docs: {resource.pop('docs', '')}\n"
        )
        for key, value in sorted(resource.items()):
            docs += f"{key.title()}: {value}\n"
        docs = docs.strip()
        return docs

    __doc__ = property(_get_doc)

    def open_docs(self):
        if not self._resource:
            raise ValueError()
        new = 2  # open in new tab
        webbrowser.open(self._resource["docs"], new=new)


class TapiocaClientExecutor(BaseTapiocaClientExecutor):
    def __str__(self):
        return f"<{type(self).__name__} object: {self._path}>"

    def __dir__(self):
        methods = [m for m in type(self).__dict__.keys() if not m.startswith("_")]
        methods.extend(["api_params", "path", "resource", "resource_name", "session"])
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
                yield executor._wrap_in_tapioca_response(data=item)
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

        self._request_kwargs = kwargs

        context = self._get_context(
            request_method=request_method,
            refresh_token=refresh_token,
            repeat_number=repeat_number,
            request_kwargs={**self._request_kwargs},
        )
        del context["data"]

        data = None
        request_kwargs = context["request_kwargs"]
        response = context["response"]

        try:
            await self.initialize()
            self._request_kwargs = await coro_wrap(
                self._api.prepare_request_kwargs, *args, **context
            )
            response = await self._session.request(
                request_method, **self._request_kwargs
            )
            context.update({"response": response, "request_kwargs": request_kwargs})
            data = await coro_wrap(self._api.process_response, **context)
            context["data"] = data
        except ResponseProcessException as ex:

            repeat_number += 1

            self._response = response
            self._data = getattr(ex, "data", None)
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
                await coro_wrap(self._api.error_handling, ex, **context)

            propagate_exception = True

            auth_expired = await coro_wrap(
                self._api.is_authentication_expired, ex, **context
            )
            if refresh_token and auth_expired:
                self._refresh_data = await coro_wrap(
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

            if await coro_wrap(self._api.retry_request, ex, **context):
                propagate_exception = False
                return await self._make_request(
                    request_method,
                    refresh_token=False,
                    repeat_number=repeat_number,
                    *args,
                    **kwargs,
                )

            if propagate_exception:
                await coro_wrap(self._api.error_handling, ex, **context)

        except Exception as ex:
            await coro_wrap(self._api.error_handling, ex, *args, **context)

        return self._wrap_in_tapioca_response(
            data=data, response=response, request_kwargs=self._request_kwargs
        )

    @staticmethod
    def _reached_max_limits(page_count, item_count, max_pages, max_items):
        reached_page_limit = max_pages is not None and max_pages <= page_count
        reached_item_limit = max_items is not None and max_items <= item_count
        return reached_page_limit or reached_item_limit

    def _get_iterator_list(self):
        return self._api.get_iterator_list(**self._get_context())

    async def _get_iterator_next_request_kwargs(self):
        return await coro_wrap(
            self._api.get_iterator_next_request_kwargs, **self._get_context()
        )


class TapiocaClientResponse(BaseTapiocaClientResponse):
    def __str__(self):
        return f"<{type(self).__name__} object: {self._response}>"

    def __call__(self, *args, **kwargs):
        return self._wrap_in_tapioca_executor()

    def __dir__(self):
        methods = [m for m in type(self).__dict__.keys() if not m.startswith("_")]
        methods.extend(
            [
                "api_params",
                "path",
                "resource",
                "resource_name",
                "session",
                "response",
                "url",
                "status",
                "request_kwargs",
                "data",
            ]
        )
        return methods
