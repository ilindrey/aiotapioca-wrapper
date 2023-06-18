import json

import pytest
import pytest_asyncio

from aiotapioca import generate_wrapper_from_adapter

from .client import SimpleClientAdapter


class FooParser:
    @staticmethod
    def foo(data, index=None):
        if index is None:
            return data
        return data[index]

    @classmethod
    def spam(cls, data, index=None):
        if index is None:
            return data
        return data[index]

    def bar(self, index=None):
        if index is None:
            return self.data
        return self.data[index]


def foo_parser(data, index=None):
    if index is None:
        return data
    return data[index]


@pytest_asyncio.fixture
async def parser_client(request):
    class ParserClientAdapter(SimpleClientAdapter):
        def get_resource_mapping(self, api_params, **kwargs):
            resource_mapping = super().get_resource_mapping(api_params, **kwargs)
            resource_mapping["test"]["parsers"] = request.param
            return resource_mapping

    client = generate_wrapper_from_adapter(ParserClientAdapter)

    async with client() as c:
        yield c


@pytest.mark.parametrize("parser_client", (foo_parser,), indirect=True)
async def test_parsers_not_found(mocked, parser_client):
    data = ["a", "b", "c"]
    mocked.get(
        parser_client.test().path,
        body=json.dumps(data),
        status=200,
        content_type="application/json",
    )
    response = await parser_client.test().get()

    with pytest.raises(AttributeError):
        response.data.blablabla()


@pytest.mark.parametrize("parser_client", (foo_parser,), indirect=True)
async def test_func_parser(mocked, parser_client):
    data = ["a", "b", "c"]
    mocked.get(
        parser_client.test().path,
        body=json.dumps(data),
        status=200,
        content_type="application/json",
    )
    response = await parser_client.test().get()

    assert response.data.foo_parser() == ["a", "b", "c"]
    assert response.data.foo_parser(0) == "a"
    assert response.data.foo_parser(1) == "b"
    assert response.data.foo_parser(2) == "c"
    with pytest.raises(IndexError):
        response.data.foo_parser(3)


@pytest.mark.parametrize("parser_client", (FooParser.foo,), indirect=True)
async def test_static_method_parser(mocked, parser_client):
    data = ["a", "b", "c"]
    mocked.get(
        parser_client.test().path,
        body=json.dumps(data),
        status=200,
        content_type="application/json",
    )
    response = await parser_client.test().get()

    assert response.data.foo() == ["a", "b", "c"]
    assert response.data.foo(0) == "a"
    assert response.data.foo(1) == "b"
    assert response.data.foo(2) == "c"
    with pytest.raises(IndexError):
        response.data.foo(3)


@pytest.mark.parametrize("parser_client", (FooParser.spam,), indirect=True)
async def test_class_method_parser(mocked, parser_client):
    data = ["a", "b", "c"]
    mocked.get(
        parser_client.test().path,
        body=json.dumps(data),
        status=200,
        content_type="application/json",
    )
    response = await parser_client.test().get()

    assert response.data.spam() == ["a", "b", "c"]
    assert response.data.spam(0) == "a"
    assert response.data.spam(1) == "b"
    assert response.data.spam(2) == "c"
    with pytest.raises(IndexError):
        response.data.spam(3)


@pytest.mark.parametrize("parser_client", (FooParser,), indirect=True)
async def test_class_parser(mocked, parser_client):
    data = ["a", "b", "c"]
    mocked.get(
        parser_client.test().path,
        body=json.dumps(data),
        status=200,
        content_type="application/json",
    )
    response = await parser_client.test().get()

    parser = response.data.foo_parser()
    assert parser.bar() == ["a", "b", "c"]
    assert parser.bar(0) == "a"
    assert parser.bar(1) == "b"
    assert parser.bar(2) == "c"
    with pytest.raises(IndexError):
        parser.bar(3)


@pytest.mark.parametrize(
    "parser_client",
    (
        {
            "func_parser": foo_parser,
            "static_method_parser": FooParser.foo,
            "class_parser": FooParser,
        },
    ),
    indirect=True,
)
async def test_dict_parser(mocked, parser_client):
    data = ["a", "b", "c"]
    mocked.get(
        parser_client.test().path,
        body=json.dumps(data),
        status=200,
        content_type="application/json",
    )
    response = await parser_client.test().get()

    assert response.data.func_parser() == ["a", "b", "c"]
    assert response.data.func_parser(1) == "b"

    assert response.data.static_method_parser() == ["a", "b", "c"]
    assert response.data.static_method_parser(1) == "b"

    assert response.data.class_parser().bar() == ["a", "b", "c"]
    assert response.data.class_parser().bar(1) == "b"
