import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


async def test_health_database_connected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    data = response.json()
    assert data["checks"]["database"] == "healthy", "Database is not healthy"


async def test_health_redis_connected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    data = response.json()
    assert data["checks"]["redis"] == "healthy", "Redis is not healthy"


async def test_health_overall_status(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "healthy", (
        f"Overall status unhealthy. DB: {data['checks']['database']}, "
        f"Redis: {data['checks']['redis']}"
    )


async def test_health_response_shape(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
