from httpx import AsyncClient


async def test_meta(client: AsyncClient) -> None:
    response = await client.get("/api/v1/meta")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Personal Learning OS API",
        "version": "0.1.0",
        "environment": "test",
    }


async def test_request_id_is_preserved(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-ID": "test-request-id"})

    assert response.headers["X-Request-ID"] == "test-request-id"


async def test_not_found_uses_common_error_shape(client: AsyncClient) -> None:
    response = await client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Not Found",
            "details": {},
        }
    }
