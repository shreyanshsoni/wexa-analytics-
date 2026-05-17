"""Phase 2 — API key lifecycle and RBAC regression tests."""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, create_api_key, signup_user, unique_email, unique_org

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE = "/api/v1"


# ── Create ────────────────────────────────────────────────────────────────────

class TestCreateApiKey:
    async def test_owner_can_create(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]

        res = await client.post(
            f"{BASE}/api-keys",
            headers=auth_headers(token),
            json={"name": "my-key"},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["id"]
        assert data["name"] == "my-key"
        assert data["key"].startswith("wxa_")      # format per spec
        assert data["key_prefix"].startswith("wxa_")

    async def test_raw_key_shown_in_creation_only(self, client: AsyncClient) -> None:
        """After creation, listing keys must NOT expose the raw key."""
        signup = await signup_user(client)
        token = signup["data"]["access_token"]

        created = await create_api_key(client, token, "list-test-key")
        raw_key = created["key"]

        list_res = await client.get(f"{BASE}/api-keys", headers=auth_headers(token))
        assert list_res.status_code == 200
        keys = list_res.json()["data"]
        assert all("key" not in k for k in keys)          # raw key never in list
        assert any(k["key_prefix"] == created["key_prefix"] for k in keys)

    async def test_missing_name_returns_422(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]

        res = await client.post(f"{BASE}/api-keys", headers=auth_headers(token), json={})
        assert res.status_code == 422

    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/api-keys", json={"name": "k"})
        assert res.status_code == 401


# ── List ──────────────────────────────────────────────────────────────────────

class TestListApiKeys:
    async def test_owner_can_list(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        await create_api_key(client, token)

        res = await client.get(f"{BASE}/api-keys", headers=auth_headers(token))
        assert res.status_code == 200
        assert isinstance(res.json()["data"], list)

    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/api-keys")
        assert res.status_code == 401

    async def test_org_isolation_cannot_see_other_org_keys(self, client: AsyncClient) -> None:
        signup_a = await signup_user(client)
        signup_b = await signup_user(client)
        token_a = signup_a["data"]["access_token"]
        token_b = signup_b["data"]["access_token"]

        await create_api_key(client, token_a, "org-a-key")

        # Org B lists keys — must not see Org A's key
        res = await client.get(f"{BASE}/api-keys", headers=auth_headers(token_b))
        assert res.status_code == 200
        assert all(k["name"] != "org-a-key" for k in res.json()["data"])


# ── Revoke ────────────────────────────────────────────────────────────────────

class TestRevokeApiKey:
    async def test_owner_can_revoke(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        key = await create_api_key(client, token)

        res = await client.post(
            f"{BASE}/api-keys/{key['id']}/revoke",
            headers=auth_headers(token),
        )
        assert res.status_code == 200

    async def test_revoked_key_marked_inactive(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        key = await create_api_key(client, token)

        await client.post(f"{BASE}/api-keys/{key['id']}/revoke", headers=auth_headers(token))

        keys = (await client.get(f"{BASE}/api-keys", headers=auth_headers(token))).json()["data"]
        target = next((k for k in keys if k["id"] == key["id"]), None)
        assert target is not None
        assert target["is_active"] is False

    async def test_revoke_wrong_org_key_returns_error(self, client: AsyncClient) -> None:
        signup_a = await signup_user(client)
        signup_b = await signup_user(client)
        token_a = signup_a["data"]["access_token"]
        token_b = signup_b["data"]["access_token"]

        key_a = await create_api_key(client, token_a)

        # Org B tries to revoke Org A's key → must fail (404 or 403)
        res = await client.post(
            f"{BASE}/api-keys/{key_a['id']}/revoke",
            headers=auth_headers(token_b),
        )
        assert res.status_code in (403, 404)

    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        import uuid
        res = await client.post(f"{BASE}/api-keys/{uuid.uuid4()}/revoke")
        assert res.status_code == 401


# ── Rotate ────────────────────────────────────────────────────────────────────

class TestRotateApiKey:
    async def test_owner_can_rotate(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        old_key = await create_api_key(client, token)

        res = await client.post(
            f"{BASE}/api-keys/{old_key['id']}/rotate",
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        new_key = res.json()["data"]
        assert new_key["key"].startswith("wxa_")
        assert new_key["key"] != old_key["key"]

    async def test_old_key_deactivated_after_rotation(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        old_key = await create_api_key(client, token)

        await client.post(f"{BASE}/api-keys/{old_key['id']}/rotate", headers=auth_headers(token))

        keys = (await client.get(f"{BASE}/api-keys", headers=auth_headers(token))).json()["data"]
        old = next((k for k in keys if k["id"] == old_key["id"]), None)
        assert old is None or old["is_active"] is False

    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        import uuid
        res = await client.post(f"{BASE}/api-keys/{uuid.uuid4()}/rotate")
        assert res.status_code == 401
