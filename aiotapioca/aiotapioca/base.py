
from aiohttp import ClientSession


class BaseTapiocaClient:
    def __init__(self, api, session=None, api_params=None, *args, **kwargs):
        self._api = api
        self._session = session
        self._api_params = api_params or {}

    def __str__(self):
        return f"<{type(self).__name__} object>"

    @property
    def closed(self):
        return self._session is None or self._session.closed

    async def initialize(self):
        if self.closed:
            self._session = ClientSession()
        return self

    def _repr_pretty_(self, p, cycle):  # IPython
        p.text(self.__str__())

    def _get_context(self, **kwargs):
        context = {
            key[1:]: value
            for key, value in self.__dict__.items()
            if key.startswith("_") and not key.startswith("__")
        }
        context.update(kwargs)
        return context

    def _wrap_in_tapioca_resource(self, *args, **kwargs):
        context = self._get_context(**kwargs)
        from .aiotapioca import TapiocaClientResource
        return TapiocaClientResource(*args, **context)


class BaseTapiocaResourceClient(BaseTapiocaClient):
    def __init__(self, client = None, path=None, resource=None, resource_name=None, *args, **kwargs):
        self._client = client
        self._path = path
        self._resource = resource
        self._resource_name = resource_name
        super().__init__(*args, **kwargs)

    async def initialize(self):
        await super().initialize()
        self._client._session = self._session
        return self._client

    def _wrap_in_tapioca_executor(self, *args, **kwargs):
        context = self._get_context(**kwargs)
        from .aiotapioca import TapiocaClientExecutor
        return TapiocaClientExecutor(*args, **context)


class BaseTapiocaExecutorClient(BaseTapiocaResourceClient):
    def __init__(self, response=None, data=None, request_kwargs=None, *args, **kwargs):
        self._response = response
        self._data = data
        self._request_kwargs = request_kwargs or {}
        super().__init__(*args, **kwargs)

    def _wrap_in_tapioca_response(self, *args, **kwargs):
        context = self._get_context(**kwargs)
        from .aiotapioca import TapiocaClientResponse
        return TapiocaClientResponse(*args, **context)


class BaseTapiocaResponseClient(BaseTapiocaExecutorClient):

    pass
