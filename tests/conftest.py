import pytest
import pytest_asyncio
from aioresponses import aioresponses

from aiotapioca import SimpleSerializer, PydanticSerializer
from .clients import (
    SimpleClient,
    SerializerClient,
    TokenRefreshByDefaultClient,
    XMLClient,
    RetryRequestClient,
)


@pytest.fixture()
def mocked():
    with aioresponses() as m:
        yield m


@pytest_asyncio.fixture
async def client():
    async with SimpleClient() as c:
        yield c


@pytest_asyncio.fixture
async def client_serializer_class():
    async with SimpleClient(serializer_class=SimpleSerializer) as c:
        yield c


@pytest_asyncio.fixture
async def serializer_client():
    async with SerializerClient() as c:
        yield c


@pytest_asyncio.fixture
async def pydantic_client():
    async with SimpleClient(serializer_class=PydanticSerializer) as c:
        yield c


@pytest_asyncio.fixture
async def xml_client():
    async with XMLClient() as c:
        yield c


@pytest_asyncio.fixture
async def token_refresh_by_default_client():
    async with TokenRefreshByDefaultClient(token="token") as c:
        yield c


@pytest_asyncio.fixture
async def retry_request_client():
    async with RetryRequestClient() as c:
        yield c


@pytest.fixture()
def serializer():
    yield SimpleSerializer()


@pytest.fixture()
def refresh_token_possible_false_values():
    yield False, None, 1, 0, "511", -22, 41, [], tuple(), {}, set(), [41], {
        "key": "value"
    }
