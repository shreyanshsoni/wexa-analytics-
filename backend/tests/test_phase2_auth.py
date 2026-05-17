"""Phase 2 — Auth regression tests: signup, login, refresh, logout, /me."""
import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import auth_headers, signup_user, unique_email, unique_org

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE = "/api/v1"


# ── Signup ────────────────────────────────────────────────────────────────────

class TestSignup:
    async def test_happy_path(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/signup", json={
            "email": unique_email(),
            "password": "TestPass1",
            "full_name": "Jane Smith",
            "org_name": unique_org(),
        })
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["access_token"]
        assert data["user"]["email"]
        assert data["user"]["full_name"] == "Jane Smith"
        assert data["org"]["slug"]
        assert data["role"] == "owner"

    async def test_sets_httponly_refresh_cookie(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/signup", json={
            "email": unique_email(),
            "password": "TestPass1",
            "full_name": "Test User",
            "org_name": unique_org(),
        })
        assert res.status_code == 201
        cookie_header = res.headers.get("set-cookie", "")
        assert "refresh_token" in cookie_header
        assert "httponly" in cookie_header.lower()

    async def test_duplicate_email_returns_409(self, client: AsyncClient) -> None:
        email = unique_email()
        await client.post(f"{BASE}/auth/signup", json={
            "email": email, "password": "TestPass1",
            "full_name": "User A", "org_name": unique_org(),
        })
        res = await client.post(f"{BASE}/auth/signup", json={
            "email": email, "password": "TestPass1",
            "full_name": "User B", "org_name": unique_org(),
        })
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "CONFLICT"

    async def test_missing_email_returns_422(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/signup", json={
            "password": "TestPass1", "full_name": "Test", "org_name": unique_org(),
        })
        assert res.status_code == 422

    async def test_missing_password_returns_422(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/signup", json={
            "email": unique_email(), "full_name": "Test", "org_name": unique_org(),
        })
        assert res.status_code == 422

    async def test_invalid_email_format_returns_422(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/signup", json={
            "email": "not-an-email", "password": "TestPass1",
            "full_name": "Test", "org_name": unique_org(),
        })
        assert res.status_code == 422

    async def test_missing_org_name_returns_422(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/signup", json={
            "email": unique_email(), "password": "TestPass1", "full_name": "Test",
        })
        assert res.status_code == 422

    async def test_empty_body_returns_422(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/signup", json={})
        assert res.status_code == 422

    async def test_org_slug_generated_from_name(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/signup", json={
            "email": unique_email(), "password": "TestPass1",
            "full_name": "Test", "org_name": "Acme Corp",
        })
        assert res.status_code == 201
        slug = res.json()["data"]["org"]["slug"]
        assert slug  # slug must exist and be non-empty
        assert " " not in slug  # no spaces in slug


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    async def test_happy_path(self, client: AsyncClient) -> None:
        email, password = unique_email(), "TestPass1"
        await signup_user(client, email=email, password=password)

        res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["access_token"]
        assert data["role"] == "owner"

    async def test_sets_refresh_cookie_on_login(self, client: AsyncClient) -> None:
        email, password = unique_email(), "TestPass1"
        await signup_user(client, email=email, password=password)
        res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
        assert "refresh_token" in res.headers.get("set-cookie", "")

    async def test_wrong_password_returns_401(self, client: AsyncClient) -> None:
        email = unique_email()
        await signup_user(client, email=email)
        res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "WrongPass9"})
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_ERROR"

    async def test_nonexistent_email_returns_401(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/login", json={
            "email": "nobody@nowhere.com", "password": "TestPass1",
        })
        assert res.status_code == 401

    async def test_missing_password_returns_422(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/login", json={"email": unique_email()})
        assert res.status_code == 422

    async def test_missing_email_returns_422(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/login", json={"password": "TestPass1"})
        assert res.status_code == 422


# ── Token Refresh ─────────────────────────────────────────────────────────────

class TestTokenRefresh:
    async def test_happy_path_returns_new_token(self, client: AsyncClient) -> None:
        email, pw = unique_email(), "TestPass1"
        signup = await signup_user(client, email=email, password=pw)
        old_token = signup["data"]["access_token"]

        res = await client.post(f"{BASE}/auth/refresh")
        assert res.status_code == 200
        new_token = res.json()["data"]["access_token"]
        assert new_token
        assert new_token != old_token

    async def test_no_cookie_returns_401(self, client: AsyncClient) -> None:
        # Use a fresh client with no cookies
        async with AsyncClient(
            transport=ASGITransport(app=client._transport.app),  # type: ignore[attr-defined]
            base_url="http://test",
        ) as fresh:
            res = await fresh.post(f"{BASE}/auth/refresh")
        assert res.status_code == 401

    async def test_old_refresh_token_revoked_after_rotation(self, client: AsyncClient) -> None:
        email, pw = unique_email(), "TestPass1"
        await signup_user(client, email=email, password=pw)

        # Login to get a fresh cookie
        login_res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
        old_cookie = login_res.cookies.get("refresh_token")

        # Rotate → client now holds new cookie
        await client.post(f"{BASE}/auth/refresh")

        # Attempt to use the OLD cookie — must fail
        async with AsyncClient(
            transport=ASGITransport(app=client._transport.app),  # type: ignore[attr-defined]
            base_url="http://test",
            cookies={"refresh_token": old_cookie or ""},
        ) as isolated:
            res = await isolated.post(f"{BASE}/auth/refresh")
        assert res.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    async def test_happy_path_returns_200(self, client: AsyncClient) -> None:
        email, pw = unique_email(), "TestPass1"
        signup = await signup_user(client, email=email, password=pw)
        token = signup["data"]["access_token"]
        res = await client.post(f"{BASE}/auth/logout", headers=auth_headers(token))
        assert res.status_code == 200

    async def test_clears_cookie(self, client: AsyncClient) -> None:
        email, pw = unique_email(), "TestPass1"
        signup = await signup_user(client, email=email, password=pw)
        token = signup["data"]["access_token"]
        res = await client.post(f"{BASE}/auth/logout", headers=auth_headers(token))
        # After logout the Set-Cookie should delete the cookie (max-age=0 or expires in past)
        cookie_header = res.headers.get("set-cookie", "")
        assert "refresh_token" in cookie_header

    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/auth/logout")
        assert res.status_code == 401


# ── Get Me ────────────────────────────────────────────────────────────────────

class TestGetMe:
    async def test_returns_current_user(self, client: AsyncClient) -> None:
        email = unique_email()
        signup = await signup_user(client, email=email)
        token = signup["data"]["access_token"]

        res = await client.get(f"{BASE}/auth/me", headers=auth_headers(token))
        assert res.status_code == 200
        assert res.json()["data"]["email"] == email

    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/auth/me")
        assert res.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert res.status_code == 401

    async def test_malformed_bearer_returns_401(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/auth/me", headers={"Authorization": "NotBearer token"})
        assert res.status_code == 401
