from aiohttp import ClientSession
from asyncio_atexit import register as atexit_register
from orjson import dumps

from aiotapioca.exceptions import TapiocaException

from .process_data import ProcessData

__all__ = (
    "BaseTapiocaClient",
    "BaseTapiocaClientResource",
    "BaseTapiocaClientExecutor",
    "BaseTapiocaClientResponse",
)


class BaseTapiocaClient:
    def __init__(self, api, session=None, api_params=None, *args, **kwargs):
        self._api = api
        self._session = session
        self._api_params = api_params or {}

    def __str__(self):
        return f"<{type(self).__name__} object>"

    @property
    def session(self):
        return self._session

    @property
    def api_params(self):
        return self._api_params

    @property
    def closed(self):
        return (
            self._session is None
            or type(self._session) is ClientSession
            and self._session.closed
        )

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
        context = {key[1:]: value for key, value in vars(self).items()}
        context.update(kwargs)
        return context

    def _wrap_in_tapioca_resource(self, **kwargs) -> "TapiocaClientResource":
        context = self._get_context(**kwargs)
        from .client import TapiocaClientResource

        return TapiocaClientResource(**context)


class BaseTapiocaClientResource(BaseTapiocaClient):
    def __init__(
        self, client, path=None, resource=None, resource_name=None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._client = client
        self._path = path or ""
        self._resource = resource or {}
        self._resource_name = resource_name

    @property
    def path(self):
        return self._path

    @property
    def resource(self):
        return self._resource

    @property
    def resource_name(self):
        return self._resource_name

    async def initialize(self):
        await super().initialize()
        self._client._session = self._session
        return self._client

    def _wrap_in_tapioca_executor(self, **kwargs) -> "TapiocaClientExecutor":
        context = self._get_context(**kwargs)
        from .client import TapiocaClientExecutor

        return TapiocaClientExecutor(**context)


class BaseTapiocaClientExecutor(BaseTapiocaClientResource):
    def __init__(self, response=None, data=None, request_kwargs=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._response = response
        self._data = data
        self._request_kwargs = request_kwargs or {}

    def _wrap_in_tapioca_response(self, **kwargs) -> "TapiocaClientResponse":
        context = self._get_context(**kwargs)
        from .client import TapiocaClientResponse

        return TapiocaClientResponse(**context)


class BaseTapiocaClientResponse(BaseTapiocaClientExecutor):
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

    @property
    def request_kwargs(self):
        return self._request_kwargs

    @property
    def data(self):
        return ProcessData(self._api, self._data, self._resource)
