"""Shared test fixtures and helpers for all phases."""
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE = "/api/v1"


# ── client fixture ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── email mock (session-wide) — prevents real HTTP calls to Resend in tests ──

@pytest.fixture(autouse=True, scope="session")
def mock_send_invite_email():
    """Auto-mock email sending for all tests. Use mock_email fixture to inspect calls."""
    with patch("app.core.email.send_invite_email", new_callable=AsyncMock) as m:
        yield m


# ── data generators ───────────────────────────────────────────────────────────

def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@wexa-test.com"


def unique_org() -> str:
    return f"Test Org {uuid.uuid4().hex[:6]}"


# ── API helpers ───────────────────────────────────────────────────────────────

async def signup_user(
    client: AsyncClient,
    email: str | None = None,
    password: str = "TestPass1",
    full_name: str = "Test User",
    org_name: str | None = None,
) -> dict:
    res = await client.post(f"{BASE}/auth/signup", json={
        "email": email or unique_email(),
        "password": password,
        "full_name": full_name,
        "org_name": org_name or unique_org(),
    })
    assert res.status_code == 201, res.text
    return res.json()


async def create_api_key(client: AsyncClient, token: str, name: str = "test-key") -> dict:
    """Create an API key and return the full response data (includes raw key)."""
    res = await client.post(
        f"{BASE}/api-keys",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def api_key_headers(raw_key: str) -> dict:
    return {"X-API-Key": raw_key}
