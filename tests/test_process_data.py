import json

import pytest


async def test_in_operator(mocked, client):
    mocked.get(
        client.test().path,
        body='{"data": 1, "other": 2}',
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    assert "data" in response.data
    assert "other" in response.data
    assert "wat" not in response.data


async def test_transform_came_case_in_snake_case(mocked, client):
    next_url = "http://api.example.org/next_batch"

    response_data = {
        "data": {
            "key_snake": "value",
            "camelCase": "data in camel case",
            "NormalCamelCase": "data in camel case",
        },
        "paging": {"next": f"{next_url}"},
    }
    mocked.add(
        client.test().path,
        body=json.dumps(response_data),
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    assert response.data() == response_data

    assert response.data.paging.next() == next_url
    assert response.data.data.key_snake() == "value"
    assert response.data.data.camel_case() == "data in camel case"
    assert response.data.data.normal_camel_case() == "data in camel case"


async def test_should_be_able_to_access_by_index(mocked, client):
    response_data = ["a", "b", "c"]
    mocked.get(
        client.test().path,
        body=json.dumps(response_data),
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    assert response.data() == response_data

    for row_1, row_2 in zip(response.data, response_data):
        assert row_1() == row_2

    assert response.data[0]() == "a"
    assert response.data[1]() == "b"
    assert response.data[2]() == "c"


async def test_accessing_index_out_of_bounds_should_raise_index_error(mocked, client):
    response_data = ["a", "b", "c"]
    mocked.get(
        client.test().path,
        body=json.dumps(response_data),
        status=200,
        content_type="application/json",
    )

    response = await client.test().get()

    with pytest.raises(IndexError):
        response.data[3]


async def test_accessing_empty_list_should_raise_index_error(mocked, client):
    mocked.get(
        client.test().path, body="[]", status=200, content_type="application/json"
    )

    response = await client.test().get()

    with pytest.raises(IndexError):
        response.data[3]
