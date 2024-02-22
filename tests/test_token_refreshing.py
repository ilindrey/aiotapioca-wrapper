from typing import Any, Tuple

import pytest
from aioresponses import CallbackResult

from aiotapioca import generate_wrapper_from_adapter
from aiotapioca.exceptions import ClientError

from .client import SimpleClientAdapter


def callback_201(*args, **kwargs):
    return CallbackResult(status=201)


def callback_401(*args, **kwargs):
    return CallbackResult(status=401)


class TokenRefreshClientAdapter(SimpleClientAdapter):
    def is_authentication_expired(self, exception, *args, **kwargs):
        return kwargs["response"].status == 401

    def refresh_authentication(self, exception, *args, **kwargs):
        new_token = "new_token"
        kwargs["api_params"]["token"] = new_token
        return new_token


TokenRefreshClient = generate_wrapper_from_adapter(TokenRefreshClientAdapter)


class TokenRefreshByDefaultClientAdapter(TokenRefreshClientAdapter):
    refresh_token = True


TokenRefreshByDefaultClient = generate_wrapper_from_adapter(
    TokenRefreshByDefaultClientAdapter
)


class FailTokenRefreshClientAdapter(TokenRefreshByDefaultClientAdapter):
    def refresh_authentication(self, exceptions, *args, **kwargs):
        return None


FailTokenRefreshClient = generate_wrapper_from_adapter(FailTokenRefreshClientAdapter)


possible_false_values: Tuple[Any, ...] = (
    False,
    None,
    1,
    0,
    "511",
    -22,
    41,
    [],
    (),
    set(),
    [41],
    {"key": "value"},
)


async def test_not_token_refresh_client_propagates_client_error(mocked, client):
    no_refresh_client = client

    mocked.post(
        no_refresh_client.test().path,
        callback=callback_401,
        content_type="application/json",
    )

    with pytest.raises(ClientError):
        await no_refresh_client.test().post()


async def test_disable_token_refreshing_with_default_param(mocked):
    async with TokenRefreshClient(token="token") as client:
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await client.test().post()


@pytest.mark.parametrize("refresh_token", possible_false_values)
async def test_disable_token_refreshing(mocked, refresh_token):
    async with TokenRefreshClient(token="token", refresh_token=refresh_token) as client:
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await client.test().post()

    async with TokenRefreshClient(token="token") as client:
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await client.test().post(refresh_token=refresh_token)


async def test_raises_if_refresh_authentication_method_returns_false_with_default_param(
    mocked,
):
    async with FailTokenRefreshClient(token="token") as client:
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await client.test().post()


@pytest.mark.parametrize("refresh_token", possible_false_values)
async def test_raises_if_refresh_authentication_method_returns_false(
    mocked, refresh_token
):
    async with FailTokenRefreshClient(
        token="token", refresh_token=refresh_token
    ) as client:
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await client.test().post()

    async with FailTokenRefreshClient(token="token") as client:
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        with pytest.raises(ClientError):
            await client.test().post(refresh_token=refresh_token)


async def test_token_expired_automatically_refresh_authentication(mocked):
    async with TokenRefreshClient(token="token") as client:
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        mocked.post(
            client.test().path,
            callback=callback_201,
            content_type="application/json",
        )

        response = await client.test().post(refresh_token=True)

        # refresh_authentication method should be able to update api_params
        assert response.api_params["token"] == "new_token"

        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        # check that the refresh_token flag is not cyclic
        with pytest.raises(ClientError):
            await client.test().post(refresh_token=True)

    async with TokenRefreshClient(token="token", refresh_token=True) as client:
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        mocked.post(
            client.test().path,
            callback=callback_201,
            content_type="application/json",
        )

        response = await client.test().post()

        # refresh_authentication method should be able to update api_params
        assert response.api_params["token"] == "new_token"

        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        # check that the refresh_token flag is not cyclic
        with pytest.raises(ClientError):
            await client.test().post()


async def test_token_expired_automatically_refresh_authentication_by_default(mocked):
    async with TokenRefreshByDefaultClient(token="token") as client:
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        mocked.post(
            client.test().path,
            callback=callback_201,
            content_type="application/json",
        )

        response = await client.test().post()

        # refresh_authentication method should be able to update api_params
        assert response._api_params["token"] == "new_token"

        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )
        mocked.post(
            client.test().path,
            callback=callback_401,
            content_type="application/json",
        )

        # check that the refresh_token flag is not cyclic
        with pytest.raises(ClientError):
            await client.test().post()
