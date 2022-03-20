import pytest
import pytest_asyncio
from aioresponses import aioresponses

from aiotapioca.serializers import SimpleSerializer
from .clients import SimpleClient, SerializerClient, TokenRefreshClient, XMLClient


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
async def xml_client():
    async with XMLClient() as c:
        yield c


@pytest_asyncio.fixture
async def token_refresh_client():
    async with TokenRefreshClient(token="token", refresh_token_by_default=True) as c:
        yield c


@pytest.fixture()
def serializer():
    yield SimpleSerializer()


@pytest.fixture()
def mocked():
    with aioresponses() as m:
        yield m
