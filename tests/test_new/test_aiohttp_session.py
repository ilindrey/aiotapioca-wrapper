from http import HTTPMethod

import pytest
from aioresponses import aioresponses

from aiotapioca.new.client.sessions import AiohttpSession, SessionResponseData


@pytest.fixture
def mocked():
    with aioresponses() as m:
        yield m


async def test_get_data(mocked):
    url = "http://api.example.org/get/1?q=1&q=2&p=3"
    mocked.get(
        url,
        body='{"status": "ok"}',
        status=200,
        content_type="application/json",
    )
    session = AiohttpSession()
    response = await session.request(HTTPMethod.GET, url)
    assert isinstance(response, SessionResponseData)
