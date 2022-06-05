
import webbrowser
from copy import copy

from aiohttp import ClientSession
from orjson import dumps
from asyncio_atexit import register as atexit_register


class BaseTapiocaClient:
    def __init__(self, api, session=None, api_params=None, *args, **kwargs):
        self._api = api
        self._session = session
        self._api_params = api_params or {}

    def __str__(self):
        return f"<{type(self).__name__} object>"

    @property
    def closed(self):
        return self._session is None or hasattr(self._session, 'closed') and self._session.closed

    async def initialize(self):
        if self.closed:
            self._session = ClientSession(json_serialize=dumps)
            atexit_register(self.close)
        return self

    async def close(self):
        if not self.closed:
            await self._session.close()
            self._session = None

    def _repr_pretty_(self, p, cycle):  # IPython
        p.text(self.__str__())

    def _get_context(self, **kwargs):
        context = {
            key[1:]: value
            for key, value in vars(self).items()
        }
        context.update(kwargs)
        return context

    def _wrap_in_tapioca_resource(self, **kwargs) -> "TapiocaClientResource":
        context = self._get_context(**kwargs)
        from .aiotapioca import TapiocaClientResource
        return TapiocaClientResource(**context)


class BaseTapiocaClientResource(BaseTapiocaClient):
    def __init__(self, client, path=None, resource=None, resource_name=None, *args, **kwargs):
        self._client = client
        self._path = path or ''
        self._resource = resource or {}
        self._resource_name = resource_name
        super().__init__(*args, **kwargs)

    async def initialize(self):
        await super().initialize()
        self._client._session = self._session
        return self._client

    def _get_doc(self):
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

    def _wrap_in_tapioca_executor(self, **kwargs) -> "TapiocaClientExecutor":
        context = self._get_context(**kwargs)
        from .aiotapioca import TapiocaClientExecutor
        return TapiocaClientExecutor(**context)


class BaseTapiocaClientExecutor(BaseTapiocaClientResource):
    def __init__(self, response=None, data=None, request_kwargs=None, *args, **kwargs):
        self._response = response
        self._data = data
        self._request_kwargs = request_kwargs or {}
        super().__init__(*args, **kwargs)

    def _wrap_in_tapioca_response(self, **kwargs) -> "TapiocaClientResponse":
        context = self._get_context(**kwargs)
        from .aiotapioca import TapiocaClientResponse
        return TapiocaClientResponse(**context)


class BaseTapiocaClientResponse(BaseTapiocaClientExecutor):

    pass
