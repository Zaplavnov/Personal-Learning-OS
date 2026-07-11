from httpx import AsyncClient

import app.api.health as health_module


async def test_liveness_does_not_check_database(client: AsyncClient, monkeypatch) -> None:
    async def fail_if_called() -> None:
        raise AssertionError("Liveness must not access the database")

    monkeypatch.setattr(health_module, "check_database", fail_if_called)
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_checks_database(client: AsyncClient, monkeypatch) -> None:
    calls = 0

    async def database_is_ready() -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(health_module, "check_database", database_is_ready)
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "available"}
    assert calls == 1


async def test_readiness_uses_api_error_format(client: AsyncClient, monkeypatch) -> None:
    async def database_is_down() -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(health_module, "check_database", database_is_down)
    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "Database is not ready",
            "details": {"database": "unavailable"},
        }
    }
