from abc import ABC, abstractmethod
from dataclasses import dataclass
from http import HTTPMethod, HTTPStatus  # TODO: HTTPMethod available in 3.11
from typing import Any, Protocol

import aiohttp
import asyncio_atexit  # type: ignore
from yarl import URL


class SessionT(Protocol):
    async def request(self, *args: Any, **kwargs: Any) -> Any: ...
    async def close(self) -> None: ...


@dataclass(frozen=True)
class SessionResponseData:
    method: HTTPMethod
    content: bytes
    status_code: HTTPStatus
    url: URL


class AbstractSession(ABC):

    @property
    @abstractmethod
    def session(self) -> SessionT:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def request(
        self, method: HTTPMethod, url: URL, *args: Any, **kwargs: Any
    ) -> SessionResponseData:
        pass


class AiohttpSession(AbstractSession):

    def __init__(self) -> None:
        self._session: SessionT | None = None

    def __del__(self) -> None:
        asyncio_atexit.register(self.close)

    @property
    def session(self) -> SessionT:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        await self.session.close()

    async def request(
        self, method: HTTPMethod, url: URL, *args: Any, **kwargs: Any
    ) -> SessionResponseData:
        try:
            response = await self.session.request(method, url, *args, **kwargs)
        except Exception:
            # TODO: handle aiohttp exceptions
            raise
        context = await response.read()
        return SessionResponseData(
            method=response.method,
            content=context,
            status_code=response.status,
            url=response.url,
        )
