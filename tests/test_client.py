import json
import pickle

from aiohttp import ClientSession

from .client import SimpleClient


class TestTapiocaClient:
    def test_available_attributes(self, client):
        dir_var = dir(client)
        resources = client._api.get_resource_mapping(client._api_params)
        expected_methods = sorted(
            [*resources, "api_params", "close", "closed", "initialize", "session"]
        )
        assert len(dir_var) == len(expected_methods)
        for attr, expected in zip(dir_var, expected_methods):
            assert attr == expected

    async def test_await_initialize(self):
        client = await SimpleClient()
        assert isinstance(client.session, ClientSession) and not client.session.closed
        assert not client.closed

    async def test_close_session(self):
        client = await SimpleClient()

        assert not client.closed

        await client.close()

        assert client.closed
        assert client.session is None

    async def test_initialize_with_context_manager(self):
        client = SimpleClient()
        await client.__aenter__()

        assert isinstance(client.session, ClientSession) and not client.session.closed
        assert not client.closed

        await client.__aexit__(None, None, None)

        assert client.closed
        assert client.session is None

    async def test_is_pickleable(self, mocked):
        pickle_client = pickle.loads(pickle.dumps(SimpleClient()))

        # ensure requests keep working after pickle:
        next_url = "http://api.example.org/next_batch"
        data = {"data": [{"key": "value"}], "paging": {"next": next_url}}
        mocked.get(
            pickle_client.test().path,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        data["paging"]["next"] = ""
        mocked.get(
            next_url,
            body=json.dumps(data),
            status=200,
            content_type="application/json",
        )

        async with pickle_client:
            response = await pickle_client.test().get()

            iterations_count = 0
            async for page in response().pages():
                assert page.data.key() == "value"
                iterations_count += 1
            assert iterations_count == 2


class TestTapiocaClientResource:
    def test_available_attributes(self, client):
        dir_var = dir(client.test)
        expected_methods = sorted(
            [
                "api_params",
                "open_docs",
                "path",
                "resource",
                "resource_name",
                "session",
                "test",
            ]
        )
        assert len(dir_var) == len(expected_methods)
        for attr, expected in zip(dir_var, expected_methods):
            assert attr == expected

    def test_fill_url_template(self, client):
        expected_url = "https://api.example.org/user/123/"
        executor = client.user(id="123")
        assert executor.path == expected_url

    def test_fill_url_from_default_params(self):
        client = SimpleClient(default_url_params={"id": 123})
        assert client.user().path == "https://api.example.org/user/123/"

    def test_fill_another_root_url_template(self, client):
        expected_url = "https://api.another.com/another-root/"
        resource = client.another_root()
        assert resource.path == expected_url

    def test_contains(self, client):
        assert "resource" in client.resource
        assert "docs" in client.resource
        assert "foo" in client.resource
        assert "spam" in client.resource

    def test_docs(self, client):
        expected = (
            f"Resource: {client.resource.resource['resource']}\n"
            f"Docs: {client.resource.resource['docs']}\n"
            f"Foo: {client.resource.resource['foo']}\n"
            f"Spam: {client.resource.resource['spam']}"
        )
        assert "\n".join(client.resource.__doc__.split("\n")[1:]) == expected
