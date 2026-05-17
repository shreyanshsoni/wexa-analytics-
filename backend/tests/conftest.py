import uuid
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── helpers ──────────────────────────────────────────────────────────────────

def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@wexa-test.com"


def unique_org() -> str:
    return f"Test Org {uuid.uuid4().hex[:6]}"


async def signup_user(
    client: AsyncClient,
    email: str | None = None,
    password: str = "TestPass1",
    full_name: str = "Test User",
    org_name: str | None = None,
) -> dict:
    res = await client.post("/api/v1/auth/signup", json={
        "email": email or unique_email(),
        "password": password,
        "full_name": full_name,
        "org_name": org_name or unique_org(),
    })
    assert res.status_code == 201, res.text
    return res.json()


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}
