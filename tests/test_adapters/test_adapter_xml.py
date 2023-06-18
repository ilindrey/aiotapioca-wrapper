from collections import OrderedDict

import pytest
import pytest_asyncio
from yarl import URL

from aiotapioca import TapiocaAdapterXML, generate_wrapper_from_adapter

from ..client import RESOURCE_MAPPING


try:
    import xmltodict  # type: ignore
except ImportError:
    pytest.skip(reason="xmltodict not installed", allow_module_level=True)


class XMLClientAdapter(TapiocaAdapterXML):
    api_root = "https://api.example.org"
    resource_mapping = RESOURCE_MAPPING


XMLClient = generate_wrapper_from_adapter(XMLClientAdapter)


@pytest_asyncio.fixture
async def xml_client():
    async with XMLClient() as c:
        yield c


async def test_xml_post_string(mocked, xml_client):
    mocked.post(
        xml_client.test().path,
        body="Any response",
        status=200,
        content_type="application/json",
    )

    data = '<tag1 attr1="val1">' "<tag2>text1</tag2>" "<tag3>text2</tag3>" "</tag1>"

    await xml_client.test().post(data=data)

    request_body = mocked.requests[("POST", URL(xml_client.test().path))][0].kwargs[
        "data"
    ]

    assert request_body == data.encode("utf-8")


async def test_xml_post_dict(mocked, xml_client):
    mocked.post(
        xml_client.test().path,
        body="Any response",
        status=200,
        content_type="application/json",
    )

    data = OrderedDict(
        [
            (
                "tag1",
                OrderedDict([("@attr1", "val1"), ("tag2", "text1"), ("tag3", "text2")]),
            )
        ]
    )

    await xml_client.test().post(data=data)

    request_body = mocked.requests[("POST", URL(xml_client.test().path))][0].kwargs[
        "data"
    ]

    assert request_body == xmltodict.unparse(data).encode("utf-8")


async def test_xml_post_dict_passes_unparse_param(mocked, xml_client):
    mocked.post(
        xml_client.test().path,
        body="Any response",
        status=200,
        content_type="application/json",
    )

    data = OrderedDict(
        [
            (
                "tag1",
                OrderedDict([("@attr1", "val1"), ("tag2", "text1"), ("tag3", "text2")]),
            )
        ]
    )

    await xml_client.test().post(data=data, xmltodict_unparse__full_document=False)

    request_body = mocked.requests[("POST", URL(xml_client.test().path))][0].kwargs[
        "data"
    ]

    assert request_body == xmltodict.unparse(data, full_document=False).encode("utf-8")


async def test_xml_returns_text_if_response_not_xml(mocked, xml_client):
    mocked.post(
        xml_client.test().path,
        body="Any response",
        status=200,
        content_type="any content",
    )

    data = OrderedDict(
        [
            (
                "tag1",
                OrderedDict([("@attr1", "val1"), ("tag2", "text1"), ("tag3", "text2")]),
            )
        ]
    )

    response = await xml_client.test().post(data=data)

    assert response.data() == "Any response"


async def test_xml_post_dict_returns_dict_if_response_xml(mocked, xml_client):
    xml_body = '<tag1 attr1="val1">text1</tag1>'
    mocked.post(
        xml_client.test().path,
        body=xml_body,
        status=200,
        content_type="application/xml",
    )

    data = OrderedDict(
        [
            (
                "tag1",
                OrderedDict([("@attr1", "val1"), ("tag2", "text1"), ("tag3", "text2")]),
            )
        ]
    )

    response = await xml_client.test().post(data=data)

    assert response.data() == xmltodict.parse(xml_body)
