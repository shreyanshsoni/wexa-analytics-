"""Phase 1 — Health endpoint regression tests."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE = "/api/v1"


class TestHealthEndpoint:
    async def test_returns_200(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/health")
        assert res.status_code == 200

    async def test_overall_status_healthy(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/health")
        assert res.json()["status"] == "healthy"

    async def test_database_healthy(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/health")
        assert res.json()["checks"]["database"] == "healthy"

    async def test_redis_healthy(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/health")
        assert res.json()["checks"]["redis"] == "healthy"

    async def test_response_shape(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/health")
        data = res.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]

    async def test_no_auth_required(self, client: AsyncClient) -> None:
        """Health is a public endpoint — must work without any token."""
        res = await client.get(f"{BASE}/health")
        assert res.status_code == 200

    async def test_wrong_method_405(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/health")
        assert res.status_code == 405
