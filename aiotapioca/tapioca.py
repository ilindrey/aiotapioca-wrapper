import copy
import asyncio
import aiohttp
import webbrowser
import json
from collections import OrderedDict

from .exceptions import ResponseProcessException


class TapiocaInstantiator:
    def __init__(self, adapter_class):
        self.adapter_class = adapter_class

    def __call__(self, serializer_class=None, session=None, **kwargs):
        refresh_token_default = kwargs.pop("refresh_token_by_default", False)
        return TapiocaClient(
            self.adapter_class(serializer_class=serializer_class),
            api_params=kwargs,
            refresh_token_by_default=refresh_token_default,
            session=session,
        )


class TapiocaClient:
    def __init__(
        self,
        api,
        data=None,
        response=None,
        request_kwargs=None,
        api_params=None,
        resource=None,
        refresh_token_by_default=False,
        refresh_data=None,
        session=None,
        *args,
        **kwargs
    ):
        self._api = api
        self._data = data
        self._response = response
        self._api_params = api_params or {}
        self._request_kwargs = request_kwargs
        self._resource = resource
        self._refresh_token_default = refresh_token_by_default
        self._refresh_data = refresh_data
        self._session = session

    async def __aenter__(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self._session is not None:
            await self._session.close()

    def _instatiate_api(self):
        serializer_class = None
        if self._api.serializer:
            serializer_class = self._api.serializer.__class__
        return self._api.__class__(serializer_class=serializer_class)

    def _wrap_in_tapioca(self, data, *args, **kwargs):
        return TapiocaClient(
            self._instatiate_api(),
            data=data,
            api_params=self._api_params,
            request_kwargs=kwargs.pop("request_kwargs", self._request_kwargs),
            response=kwargs.pop("response", self._response),
            resource=kwargs.pop("resource", self._resource),
            refresh_token_by_default=self._refresh_token_default,
            refresh_data=self._refresh_data,
            session=self._session,
            *args,
            **kwargs
        )

    def _wrap_in_tapioca_executor(self, data, *args, **kwargs):
        return TapiocaClientExecutor(
            self._instatiate_api(),
            data=data,
            api_params=self._api_params,
            request_kwargs=kwargs.pop("request_kwargs", self._request_kwargs),
            response=kwargs.pop("response", self._response),
            resource=kwargs.pop("resource", self._resource),
            refresh_token_by_default=self._refresh_token_default,
            refresh_data=self._refresh_data,
            session=self._session,
            *args,
            **kwargs
        )

    def _context(self, **kwargs):
        context = dict(
            client=self,
            api=self._api,
            data=self._data,
            response=self._response,
            api_params=self._api_params,
            request_kwargs=self._request_kwargs,
            resource=self._resource,
            refresh_token_default=self._refresh_token_default,
            refresh_data=self._refresh_data,
            session=self._session,
        )
        context.update(kwargs)
        return context

    def _get_doc(self):
        resources = copy.copy(self._resource)
        docs = (
            "Automatic generated __doc__ from resource_mapping.\n"
            "Resource: %s\n"
            "Docs: %s\n" % (resources.pop("resource", ""), resources.pop("docs", ""))
        )
        for key, value in sorted(resources.items()):
            docs += "%s: %s\n" % (key.title(), value)
        docs = docs.strip()
        return docs

    __doc__ = property(_get_doc)

    def __call__(self, *args, **kwargs):
        data = self._data

        url_params = self._api_params.get("default_url_params", {})
        url_params.update(kwargs)
        if self._resource and url_params:
            data = self._api.fill_resource_template_url(
                **self._context(url_params=url_params, template=self._data)
            )

        return self._wrap_in_tapioca_executor(
            data, resource=self._resource, response=self._response
        )

    """
    Convert a snake_case string in CamelCase.
    http://stackoverflow.com/questions/19053707/convert-snake-case-snake-case-to-lower-camel-case-lowercamelcase-in-python
    """

    def _to_camel_case(self, name):
        if isinstance(name, int):
            return name
        components = name.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    def _get_client_from_name(self, name):
        if (
            isinstance(self._data, list)
            and isinstance(name, int)
            or hasattr(self._data, "__iter__")
            and name in self._data
        ):
            return self._wrap_in_tapioca(data=self._data[name])

        # if could not access, falback to resource mapping
        resource_mapping = self._api.resource_mapping
        if name in resource_mapping:
            resource = resource_mapping[name]
            api_root = self._api.get_api_root(self._api_params, resource_name=name)

            url = api_root.rstrip("/") + "/" + resource["resource"].lstrip("/")
            return self._wrap_in_tapioca(url, resource=resource)

        return None

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

    def __getattr__(self, name):
        # Fix to be pickle-able:
        # return None for all unimplemented dunder methods
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        ret = self._get_client_from_name_or_fallback(name)
        if ret is None:
            raise AttributeError(name)
        return ret

    def __getitem__(self, key):
        ret = self._get_client_from_name_or_fallback(key)
        if ret is None:
            raise KeyError(key)
        return ret

    def __dir__(self):
        if self._api and self._data is None:
            return [key for key in self._api.resource_mapping.keys()]

        if isinstance(self._data, dict):
            return self._data.keys()

        return []

    def __str__(self):
        if type(self._data) == OrderedDict:
            return ("<{} object, printing as dict:\n" "{}>").format(
                self.__class__.__name__, json.dumps(self._data, indent=4)
            )
        else:
            import pprint

            pp = pprint.PrettyPrinter(indent=4)
            return ("<{} object\n" "{}>").format(
                self.__class__.__name__, pp.pformat(self._data)
            )

    def _repr_pretty_(self, p, cycle):
        p.text(self.__str__())

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data


class TapiocaClientExecutor(TapiocaClient):
    def __init__(self, api, *args, **kwargs):
        super().__init__(api, *args, **kwargs)

    def __getitem__(self, key):
        raise Exception(
            "This operation cannot be done on a" + " TapiocaClientExecutor object"
        )

    def __iter__(self):
        raise Exception("Cannot iterate over a TapiocaClientExecutor object")

    def __getattr__(self, name):
        # Fix to be pickle-able:
        # return None for all unimplemented dunder methods
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        if name.startswith("to_"):  # deserializing
            method = self._resource.get(name)
            kwargs = method.get("params", {}) if method else {}
            return self._api._get_to_native_method(name, self._data, **kwargs)
        return self._wrap_in_tapioca_executor(getattr(self._data, name))

    def __call__(self, *args, **kwargs):
        return self._wrap_in_tapioca(self._data.__call__(*args, **kwargs))

    @property
    def data(self):
        return self._data

    @property
    def response(self):
        if self._response is None:
            raise Exception("This instance has no response object")
        return self._response

    @property
    def status(self):
        return self.response.status

    @property
    def refresh_data(self):
        return self._refresh_data

    @staticmethod
    async def _coro_wrap(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        return result

    async def _make_request(
        self, request_method, refresh_token=None, repeat_number=0, *args, **kwargs
    ):
        if "url" not in kwargs:
            kwargs["url"] = self._data

        context = self._context(
            request_method=request_method,
            refresh_token=refresh_token,
            repeat_number=repeat_number,
            **kwargs
        )
        request_kwargs = self._api.get_request_kwargs(
            self._api_params, request_method, *args, **kwargs
        )

        response = await self._session.request(request_method, **request_kwargs)

        try:
            context.update(dict(response=response, request_kwargs=request_kwargs))
            data = await self._coro_wrap(self._api.process_response, **context)
        except ResponseProcessException as e:
            repeat_number += 1

            client = self._wrap_in_tapioca(
                e.data, response=response, request_kwargs=request_kwargs
            )

            context.update(
                dict(
                    client=client,
                    response=response,
                    request_kwargs=request_kwargs,
                    repeat_number=repeat_number,
                )
            )

            error_message = await self._coro_wrap(
                self._api.get_error_message, **{**context, "data": e.data}
            )
            tapioca_exception = e.tapioca_exception(
                message=error_message, client=client
            )

            should_refresh_token = (
                refresh_token is not False and self._refresh_token_default
            )
            auth_expired = await self._coro_wrap(
                self._api.is_authentication_expired, tapioca_exception, **context
            )

            propagate_exception = True

            if should_refresh_token and auth_expired:
                self._refresh_data = await self._coro_wrap(
                    self._api.refresh_authentication, **context
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

            # code based on
            # https://github.com/pavelmaksimov/tapi-wrapper/blob/262468e039db83e8e13564966ad96be39a3d2dab/tapi2/tapi.py#L344
            if self._api.retry_request(tapioca_exception, error_message, **context):
                return await self._make_request(
                    request_method,
                    refresh_token=False,
                    repeat_number=repeat_number,
                    *args,
                    **kwargs
                )

            if propagate_exception:
                # code based on
                # https://github.com/pavelmaksimov/tapi-wrapper/blob/262468e039db83e8e13564966ad96be39a3d2dab/tapi2/tapi.py#L344
                self._api.error_handling(tapioca_exception, error_message, **context)

        return self._wrap_in_tapioca(
            data, response=response, request_kwargs=request_kwargs
        )

    async def _send(self, request_method, *args, **kwargs):

        if "semaphore" in kwargs and "semaphore_class" not in kwargs:
            kwargs["semaphore_class"] = asyncio.Semaphore(kwargs.get("semaphore", 10))

        debug = kwargs.pop("debug") if "debug" in kwargs else False
        semaphore = (
            kwargs.pop("semaphore_class")
            if "semaphore_class" in kwargs
            else asyncio.Semaphore()
        )

        async with semaphore:
            response = await self._make_request(request_method, *args, **kwargs)

        if debug:
            response_info = "status: {} - response data: {}".format(
                response().status, str(response().data)[:33]
            )
            print(response_info)

        return response

    async def _send_batch(self, request_method, *args, **kwargs):

        data = kwargs.pop("data") if "data" in kwargs else []

        kwargs["semaphore_class"] = asyncio.Semaphore(kwargs.get("semaphore", 10))

        results = await asyncio.gather(
            *[
                self._send(request_method, *args, **{**kwargs, "data": row})
                for row in data
            ]
        )

        return results

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

    def _get_iterator_list(self):
        return self._api.get_iterator_list(**self._context())

    async def _get_iterator_next_request_kwargs(self):
        return await self._coro_wrap(
            self._api.get_iterator_next_request_kwargs, **self._context()
        )

    @staticmethod
    def _reached_max_limits(page_count, item_count, max_pages, max_items):
        reached_page_limit = max_pages is not None and max_pages <= page_count
        reached_item_limit = max_items is not None and max_items <= item_count
        return reached_page_limit or reached_item_limit

    async def pages(self, max_pages=None, max_items=None, **kwargs):
        executor = self
        iterator_list = executor._get_iterator_list()
        page_count = 0
        item_count = 0

        while iterator_list:
            if executor._reached_max_limits(
                page_count, item_count, max_pages, max_items
            ):
                break
            for item in iterator_list:
                if executor._reached_max_limits(
                    page_count, item_count, max_pages, max_items
                ):
                    break
                yield executor._wrap_in_tapioca(item)
                item_count += 1

            page_count += 1

            next_request_kwargs = await executor._get_iterator_next_request_kwargs()

            if not next_request_kwargs:
                break

            response = await executor.get(**next_request_kwargs)
            executor = response()
            iterator_list = executor._get_iterator_list()

    def open_docs(self):
        if not self._resource:
            raise KeyError()

        new = 2  # open in new tab
        webbrowser.open(self._resource["docs"], new=new)

    def open_in_browser(self):
        new = 2  # open in new tab
        webbrowser.open(self._data, new=new)

    def __dir__(self):
        methods = [
            m for m in TapiocaClientExecutor.__dict__.keys() if not m.startswith("_")
        ]
        methods += [m for m in dir(self._api.serializer) if m.startswith("to_")]

        return methods
