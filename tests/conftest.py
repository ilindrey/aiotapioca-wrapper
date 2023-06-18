import pytest
import pytest_asyncio
from aioresponses import aioresponses

from .client import SimpleClient


@pytest.fixture
def mocked():
    with aioresponses() as m:
        yield m


@pytest_asyncio.fixture
async def client():
    yield SimpleClient()
