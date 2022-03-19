
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from aiotapioca.serializers import SimpleSerializer
from .client import SimpleClient, SerializerClient


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


@pytest.fixture()
def serializer():
    yield SimpleSerializer()


@pytest.fixture()
def mocked():
    with aioresponses() as m:
        yield m
