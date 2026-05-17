"""Phase 3 — Data ingestion regression tests: events, batch, CSV, stats, isolation."""
import io
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import api_key_headers, auth_headers, create_api_key, signup_user, unique_email

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE = "/api/v1"

_MOCK_TASK = "app.workers.tasks.ingestion_tasks.process_event"
_MOCK_BATCH = "app.workers.tasks.ingestion_tasks.process_batch_events"
_MOCK_CSV   = "app.workers.tasks.ingestion_tasks.process_csv_upload"


async def _setup_org_with_key(client: AsyncClient) -> tuple[str, str]:
    """Return (jwt_token, raw_api_key) for a new owner org."""
    signup = await signup_user(client)
    token = signup["data"]["access_token"]
    key_data = await create_api_key(client, token)
    return token, key_data["key"]


# ── Single Event ──────────────────────────────────────────────────────────────

class TestIngestSingleEvent:
    async def test_event_name_field_returns_202(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        with patch(_MOCK_TASK) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/events",
                headers=api_key_headers(raw_key),
                json={"event_name": "page_view", "properties": {"url": "/home"}},
            )
        assert res.status_code == 202
        data = res.json()["data"]
        assert data["accepted"] == 1
        assert data["batch_id"]
        mock.delay.assert_called_once()

    async def test_event_alias_field_returns_202(self, client: AsyncClient) -> None:
        """Spec uses "event" as field name in curl examples — both must work."""
        _, raw_key = await _setup_org_with_key(client)
        with patch(_MOCK_TASK) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/events",
                headers=api_key_headers(raw_key),
                json={"event": "button_click", "properties": {"label": "signup"}},
            )
        assert res.status_code == 202
        mock.delay.assert_called_once()

    async def test_with_explicit_timestamp(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        with patch(_MOCK_TASK) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/events",
                headers=api_key_headers(raw_key),
                json={"event_name": "purchase", "timestamp": "2024-01-15T10:00:00Z",
                      "properties": {"amount": 99.99}},
            )
        assert res.status_code == 202

    async def test_without_timestamp_defaults_to_now(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        with patch(_MOCK_TASK) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/events",
                headers=api_key_headers(raw_key),
                json={"event_name": "signup"},
            )
        assert res.status_code == 202

    async def test_empty_properties_allowed(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        with patch(_MOCK_TASK) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/events",
                headers=api_key_headers(raw_key),
                json={"event_name": "ping", "properties": {}},
            )
        assert res.status_code == 202

    async def test_no_api_key_returns_401(self, client: AsyncClient) -> None:
        res = await client.post(
            f"{BASE}/ingest/events",
            json={"event_name": "page_view"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_ERROR"

    async def test_invalid_api_key_returns_401(self, client: AsyncClient) -> None:
        res = await client.post(
            f"{BASE}/ingest/events",
            headers={"X-API-Key": "wxa_totally_fake_key_abc123"},
            json={"event_name": "page_view"},
        )
        assert res.status_code in (401, 403)

    async def test_revoked_api_key_returns_401(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        key_data = await create_api_key(client, token, "to-revoke")

        # Revoke the key
        await client.post(
            f"{BASE}/api-keys/{key_data['id']}/revoke",
            headers=auth_headers(token),
        )

        res = await client.post(
            f"{BASE}/ingest/events",
            headers=api_key_headers(key_data["key"]),
            json={"event_name": "test"},
        )
        assert res.status_code in (401, 403)

    async def test_missing_event_name_returns_422(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        res = await client.post(
            f"{BASE}/ingest/events",
            headers=api_key_headers(raw_key),
            json={"properties": {"url": "/home"}},
        )
        assert res.status_code == 422

    async def test_empty_event_name_returns_422(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        res = await client.post(
            f"{BASE}/ingest/events",
            headers=api_key_headers(raw_key),
            json={"event_name": ""},
        )
        assert res.status_code == 422

    async def test_empty_body_returns_422(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        res = await client.post(
            f"{BASE}/ingest/events",
            headers=api_key_headers(raw_key),
            json={},
        )
        assert res.status_code == 422


# ── Batch Events ──────────────────────────────────────────────────────────────

class TestIngestBatch:
    async def test_valid_batch_returns_202(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        with patch(_MOCK_BATCH) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/events/batch",
                headers=api_key_headers(raw_key),
                json={"events": [
                    {"event_name": "page_view", "properties": {"url": "/"}},
                    {"event": "click", "properties": {"element": "btn"}},
                    {"event_name": "signup"},
                ]},
            )
        assert res.status_code == 202
        data = res.json()["data"]
        assert data["accepted"] == 3
        assert data["batch_id"]
        mock.delay.assert_called_once()

    async def test_batch_of_one_returns_202(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        with patch(_MOCK_BATCH) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/events/batch",
                headers=api_key_headers(raw_key),
                json={"events": [{"event_name": "solo"}]},
            )
        assert res.status_code == 202

    async def test_empty_events_list_returns_422(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        res = await client.post(
            f"{BASE}/ingest/events/batch",
            headers=api_key_headers(raw_key),
            json={"events": []},
        )
        assert res.status_code == 422

    async def test_exceeding_1000_events_returns_422(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        events = [{"event_name": f"event_{i}"} for i in range(1001)]
        res = await client.post(
            f"{BASE}/ingest/events/batch",
            headers=api_key_headers(raw_key),
            json={"events": events},
        )
        assert res.status_code == 422

    async def test_exactly_1000_events_returns_202(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        events = [{"event_name": f"event_{i}"} for i in range(1000)]
        with patch(_MOCK_BATCH) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/events/batch",
                headers=api_key_headers(raw_key),
                json={"events": events},
            )
        assert res.status_code == 202

    async def test_no_api_key_returns_401(self, client: AsyncClient) -> None:
        res = await client.post(
            f"{BASE}/ingest/events/batch",
            json={"events": [{"event_name": "test"}]},
        )
        assert res.status_code == 401

    async def test_missing_events_key_returns_422(self, client: AsyncClient) -> None:
        _, raw_key = await _setup_org_with_key(client)
        res = await client.post(
            f"{BASE}/ingest/events/batch",
            headers=api_key_headers(raw_key),
            json={},
        )
        assert res.status_code == 422


# ── CSV Upload ────────────────────────────────────────────────────────────────

class TestCsvUpload:
    def _make_csv(self, rows: list[str]) -> bytes:
        content = "\n".join(rows)
        return content.encode("utf-8")

    async def test_valid_csv_analyst_returns_202(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        owner_token = signup["data"]["access_token"]
        csv_bytes = self._make_csv([
            "event_name,timestamp,url",
            "page_view,2024-01-01T10:00:00Z,/home",
            "signup,,/signup",
        ])
        with patch(_MOCK_CSV) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/csv",
                headers=auth_headers(owner_token),
                files={"file": ("events.csv", io.BytesIO(csv_bytes), "text/csv")},
            )
        assert res.status_code == 202
        data = res.json()["data"]
        assert data["upload_id"]
        assert "accepted" in data["message"].lower() or "bytes" in data["message"].lower()

    async def test_csv_with_event_name_column(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        csv_bytes = self._make_csv([
            "event_name,url",
            "page_view,/about",
        ])
        with patch(_MOCK_CSV) as mock:
            mock.delay.return_value = MagicMock()
            res = await client.post(
                f"{BASE}/ingest/csv",
                headers=auth_headers(token),
                files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
            )
        assert res.status_code == 202

    async def test_non_csv_file_returns_422(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        res = await client.post(
            f"{BASE}/ingest/csv",
            headers=auth_headers(token),
            files={"file": ("data.json", io.BytesIO(b'{"key":"val"}'), "application/json")},
        )
        assert res.status_code == 422

    async def test_no_auth_returns_401(self, client: AsyncClient) -> None:
        csv_bytes = self._make_csv(["event_name", "test"])
        res = await client.post(
            f"{BASE}/ingest/csv",
            files={"file": ("events.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert res.status_code == 401

    async def test_file_over_10mb_returns_422(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        # 11 MB of data
        big_content = b"event_name\n" + b"page_view\n" * (11 * 1024 * 1024 // 10)
        res = await client.post(
            f"{BASE}/ingest/csv",
            headers=auth_headers(token),
            files={"file": ("big.csv", io.BytesIO(big_content), "text/csv")},
        )
        assert res.status_code == 422

    async def test_viewer_cannot_upload_csv(self, client: AsyncClient) -> None:
        """Viewer role must get 403 on CSV upload (requires Analyst+)."""
        signup = await signup_user(client)
        owner_token = signup["data"]["access_token"]
        viewer_email = unique_email()

        await client.post(
            f"{BASE}/organizations/invite",
            headers=auth_headers(owner_token),
            json={"email": viewer_email, "role": "viewer"},
        )
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.invite import Invite

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Invite).where(Invite.email == viewer_email))
            invite = result.scalar_one_or_none()

        if not invite:
            pytest.skip("Invite not found")

        accept_res = await client.post(
            f"{BASE}/auth/invite/{invite.token}/accept",
            json={"full_name": "Viewer", "password": "TestPass1"},
        )
        viewer_token = accept_res.json()["data"]["access_token"]

        csv_bytes = self._make_csv(["event_name", "test"])
        res = await client.post(
            f"{BASE}/ingest/csv",
            headers=auth_headers(viewer_token),
            files={"file": ("events.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert res.status_code == 403


# ── Stats ─────────────────────────────────────────────────────────────────────

class TestIngestionStats:
    async def test_returns_200_with_correct_shape(self, client: AsyncClient) -> None:
        signup = await signup_user(client)
        token = signup["data"]["access_token"]

        res = await client.get(f"{BASE}/ingest/stats", headers=auth_headers(token))
        assert res.status_code == 200
        data = res.json()["data"]
        assert "total_today" in data
        assert "total_week" in data
        assert "total_month" in data
        assert "total_all_time" in data
        assert all(isinstance(data[k], int) for k in data)

    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/ingest/stats")
        assert res.status_code == 401

    async def test_stats_reflect_stored_events(self, client: AsyncClient) -> None:
        """Store 2 events directly via internal helper, verify stats increase."""
        import uuid
        from datetime import UTC, datetime

        from app.core.database import AsyncSessionLocal
        from app.models.event import Event

        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        org_id = uuid.UUID(signup["data"]["org"]["id"])

        # Get baseline
        base_res = await client.get(f"{BASE}/ingest/stats", headers=auth_headers(token))
        base_all_time = base_res.json()["data"]["total_all_time"]

        # Directly store 2 events
        async with AsyncSessionLocal() as db:
            db.add_all([
                Event(
                    organization_id=org_id,
                    event_name="test_event",
                    properties={},
                    timestamp=datetime.now(UTC),
                    source="api",
                ),
                Event(
                    organization_id=org_id,
                    event_name="test_event",
                    properties={"key": "val"},
                    timestamp=datetime.now(UTC),
                    source="api",
                ),
            ])
            await db.commit()

        # Verify stats increased by exactly 2
        after_res = await client.get(f"{BASE}/ingest/stats", headers=auth_headers(token))
        assert after_res.json()["data"]["total_all_time"] == base_all_time + 2


# ── Org Isolation ─────────────────────────────────────────────────────────────

class TestIngestionOrgIsolation:
    async def test_api_key_scoped_to_org(self, client: AsyncClient) -> None:
        """Events ingested via Org A's key must never appear in Org B's stats."""
        import uuid
        from datetime import UTC, datetime
        from app.core.database import AsyncSessionLocal
        from app.models.event import Event

        signup_a = await signup_user(client)
        signup_b = await signup_user(client)
        token_b = signup_b["data"]["access_token"]
        org_b_id = uuid.UUID(signup_b["data"]["org"]["id"])

        # Get Org B baseline
        base = (await client.get(f"{BASE}/ingest/stats", headers=auth_headers(token_b))).json()
        base_all = base["data"]["total_all_time"]

        # Insert 5 events directly for Org A (not Org B)
        org_a_id = uuid.UUID(signup_a["data"]["org"]["id"])
        async with AsyncSessionLocal() as db:
            db.add_all([
                Event(
                    organization_id=org_a_id,
                    event_name="secret",
                    properties={},
                    timestamp=datetime.now(UTC),
                    source="api",
                )
                for _ in range(5)
            ])
            await db.commit()

        # Org B's stats must be unchanged
        after = (await client.get(f"{BASE}/ingest/stats", headers=auth_headers(token_b))).json()
        assert after["data"]["total_all_time"] == base_all

    async def test_cannot_use_jwt_on_ingest_endpoint(self, client: AsyncClient) -> None:
        """Ingest endpoint requires X-API-Key, not Bearer token."""
        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        res = await client.post(
            f"{BASE}/ingest/events",
            headers=auth_headers(token),   # JWT instead of API key
            json={"event_name": "test"},
        )
        assert res.status_code == 401


# ── Rate Limiting ─────────────────────────────────────────────────────────────

class TestRateLimiting:
    async def test_rate_limit_exceeded_returns_429(self, client: AsyncClient) -> None:
        """Mock Redis to simulate rate limit breach — verify 429 response."""
        _, raw_key = await _setup_org_with_key(client)

        with patch("app.services.ingestion_service._check_rate_limit") as mock_rl:
            from app.core.exceptions import RateLimitError
            mock_rl.side_effect = RateLimitError("Rate limit exceeded (1000/min). Retry after 60 seconds.")
            res = await client.post(
                f"{BASE}/ingest/events",
                headers=api_key_headers(raw_key),
                json={"event_name": "flood"},
            )
        assert res.status_code == 429
        assert res.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
