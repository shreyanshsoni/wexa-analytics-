"""Phase 4 — Dashboards, Widgets, Saved Queries: comprehensive regression tests."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import auth_headers, signup_user, unique_email, unique_org

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE = "/api/v1"

# ── Shared helpers ────────────────────────────────────────────────────────────

_QUERY_PAYLOAD = {
    "name": "Page Views",
    "event_name": "page_view",
    "aggregation": "count",
    "group_by": "hour",
    "time_range": "24h",
    "filters": [],
}

_DASHBOARD_PAYLOAD = {"name": "My Dashboard", "description": "Test"}

_WIDGET_POSITION = {"x": 0, "y": 0, "w": 6, "h": 4}


async def _new_owner(client: AsyncClient) -> tuple[str, str]:
    """Return (token, org_id) for a freshly created owner."""
    res = await signup_user(client)
    d = res["data"]
    return d["access_token"], d["org"]["id"]


async def _create_dashboard(client: AsyncClient, token: str, **extra) -> dict:
    payload = {**_DASHBOARD_PAYLOAD, **extra}
    res = await client.post(f"{BASE}/dashboards", json=payload, headers=auth_headers(token))
    assert res.status_code == 201, res.text
    return res.json()["data"]


async def _create_saved_query(client: AsyncClient, token: str, **extra) -> dict:
    payload = {**_QUERY_PAYLOAD, **extra}
    res = await client.post(f"{BASE}/saved-queries", json=payload, headers=auth_headers(token))
    assert res.status_code == 201, res.text
    return res.json()["data"]


async def _create_widget(
    client: AsyncClient,
    token: str,
    dashboard_id: str,
    saved_query_id: str | None = None,
    title: str = "Test Widget",
    widget_type: str = "line_chart",
) -> dict:
    payload: dict = {
        "dashboard_id": dashboard_id,
        "title": title,
        "widget_type": widget_type,
        "time_range": "24h",
        "position": _WIDGET_POSITION,
    }
    if saved_query_id:
        payload["saved_query_id"] = saved_query_id
    res = await client.post(f"{BASE}/widgets", json=payload, headers=auth_headers(token))
    assert res.status_code == 201, res.text
    return res.json()["data"]


async def _invite_and_accept(
    client: AsyncClient,
    owner_token: str,
    role: str,
) -> str:
    """Invite a new user with the given role; return their access token."""
    email = unique_email()
    await client.post(
        f"{BASE}/organizations/invite",
        headers=auth_headers(owner_token),
        json={"email": email, "role": role},
    )

    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.invite import Invite

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Invite).where(Invite.email == email))
        invite = result.scalar_one_or_none()

    assert invite is not None, "Invite not found in DB"
    accept_res = await client.post(
        f"{BASE}/auth/invite/{invite.token}/accept",
        json={"full_name": f"{role.title()} User", "password": "TestPass1"},
    )
    assert accept_res.status_code == 201, accept_res.text
    return accept_res.json()["data"]["access_token"]


# ── Saved Queries: CRUD ───────────────────────────────────────────────────────

class TestSavedQueryCRUD:
    async def test_create_returns_201_with_correct_shape(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/saved-queries",
            json=_QUERY_PAYLOAD,
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["id"]
        assert data["name"] == "Page Views"
        assert data["query_config"]["event_name"] == "page_view"
        assert data["query_config"]["aggregation"] == "count"

    async def test_list_returns_created_queries(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        await _create_saved_query(client, token, name="Q1")
        await _create_saved_query(client, token, name="Q2")
        res = await client.get(f"{BASE}/saved-queries", headers=auth_headers(token))
        assert res.status_code == 200
        names = [q["name"] for q in res.json()["data"]]
        assert "Q1" in names and "Q2" in names

    async def test_get_single_returns_correct_query(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_saved_query(client, token, name="Specific Query")
        res = await client.get(f"{BASE}/saved-queries/{created['id']}", headers=auth_headers(token))
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "Specific Query"

    async def test_update_changes_fields(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_saved_query(client, token)
        res = await client.put(
            f"{BASE}/saved-queries/{created['id']}",
            json={"name": "Updated Name", "aggregation": "sum"},
            headers=auth_headers(token),
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["name"] == "Updated Name"
        assert data["query_config"]["aggregation"] == "sum"

    async def test_delete_returns_204(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_saved_query(client, token)
        res = await client.delete(
            f"{BASE}/saved-queries/{created['id']}",
            headers=auth_headers(token),
        )
        assert res.status_code == 204

    async def test_get_deleted_query_returns_404(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_saved_query(client, token)
        await client.delete(f"{BASE}/saved-queries/{created['id']}", headers=auth_headers(token))
        res = await client.get(f"{BASE}/saved-queries/{created['id']}", headers=auth_headers(token))
        assert res.status_code == 404

    async def test_get_nonexistent_returns_404(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.get(
            f"{BASE}/saved-queries/{uuid.uuid4()}", headers=auth_headers(token)
        )
        assert res.status_code == 404

    async def test_no_auth_returns_401(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/saved-queries")
        assert res.status_code == 401

    async def test_create_without_auth_returns_401(self, client: AsyncClient) -> None:
        res = await client.post(f"{BASE}/saved-queries", json=_QUERY_PAYLOAD)
        assert res.status_code == 401

    async def test_missing_required_fields_returns_422(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/saved-queries",
            json={"name": "Missing event_name"},
            headers=auth_headers(token),
        )
        assert res.status_code == 422

    async def test_cross_org_isolation(self, client: AsyncClient) -> None:
        token_a, _ = await _new_owner(client)
        token_b, _ = await _new_owner(client)
        created = await _create_saved_query(client, token_a)
        res = await client.get(
            f"{BASE}/saved-queries/{created['id']}", headers=auth_headers(token_b)
        )
        assert res.status_code == 404


class TestSavedQueryRBAC:
    async def test_viewer_can_list_queries(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        await _create_saved_query(client, owner_token)
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.get(f"{BASE}/saved-queries", headers=auth_headers(viewer_token))
        assert res.status_code == 200

    async def test_viewer_cannot_create_query(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.post(
            f"{BASE}/saved-queries", json=_QUERY_PAYLOAD, headers=auth_headers(viewer_token)
        )
        assert res.status_code == 403

    async def test_viewer_cannot_delete_query(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        created = await _create_saved_query(client, owner_token)
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.delete(
            f"{BASE}/saved-queries/{created['id']}", headers=auth_headers(viewer_token)
        )
        assert res.status_code == 403

    async def test_analyst_can_create_query(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        analyst_token = await _invite_and_accept(client, owner_token, "analyst")
        res = await client.post(
            f"{BASE}/saved-queries", json=_QUERY_PAYLOAD, headers=auth_headers(analyst_token)
        )
        assert res.status_code == 201


# ── Dashboards: CRUD ──────────────────────────────────────────────────────────

class TestDashboardCRUD:
    async def test_create_blank_dashboard_returns_201(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/dashboards",
            json={"name": "My Board", "description": "Desc"},
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["id"]
        assert data["name"] == "My Board"
        assert data["widgets"] == []
        assert data["is_public"] is False
        assert data["share_token"] is None

    async def test_create_with_template_returns_widgets(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/dashboards",
            json={"name": "Web Board", "template_type": "web_analytics"},
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert len(data["widgets"]) > 0
        assert data["template_type"] == "web_analytics"

    async def test_create_sales_template(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/dashboards",
            json={"name": "Sales Board", "template_type": "sales"},
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        assert len(res.json()["data"]["widgets"]) > 0

    async def test_create_devops_template(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/dashboards",
            json={"name": "DevOps Board", "template_type": "devops"},
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        assert len(res.json()["data"]["widgets"]) > 0

    async def test_create_with_auto_refresh_1m(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/dashboards",
            json={"name": "Live Board", "auto_refresh_interval": "1m"},
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        assert res.json()["data"]["auto_refresh_interval"] == "1m"

    async def test_create_with_auto_refresh_30s(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/dashboards",
            json={"name": "Fast Board", "auto_refresh_interval": "30s"},
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        assert res.json()["data"]["auto_refresh_interval"] == "30s"

    async def test_create_with_auto_refresh_5m(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/dashboards",
            json={"name": "Slow Board", "auto_refresh_interval": "5m"},
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        assert res.json()["data"]["auto_refresh_interval"] == "5m"

    async def test_list_returns_created_dashboards(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        await _create_dashboard(client, token, name="Board A")
        await _create_dashboard(client, token, name="Board B")
        res = await client.get(f"{BASE}/dashboards", headers=auth_headers(token))
        assert res.status_code == 200
        names = [d["name"] for d in res.json()["data"]]
        assert "Board A" in names and "Board B" in names

    async def test_get_dashboard_returns_correct_data(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token, name="Specific Board")
        res = await client.get(f"{BASE}/dashboards/{created['id']}", headers=auth_headers(token))
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "Specific Board"

    async def test_update_dashboard_changes_name(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token)
        res = await client.put(
            f"{BASE}/dashboards/{created['id']}",
            json={"name": "Renamed Board"},
            headers=auth_headers(token),
        )
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "Renamed Board"

    async def test_delete_dashboard_returns_204(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token)
        res = await client.delete(
            f"{BASE}/dashboards/{created['id']}", headers=auth_headers(token)
        )
        assert res.status_code == 204

    async def test_get_deleted_dashboard_returns_404(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token)
        await client.delete(f"{BASE}/dashboards/{created['id']}", headers=auth_headers(token))
        res = await client.get(
            f"{BASE}/dashboards/{created['id']}", headers=auth_headers(token)
        )
        assert res.status_code == 404

    async def test_get_nonexistent_dashboard_returns_404(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.get(f"{BASE}/dashboards/{uuid.uuid4()}", headers=auth_headers(token))
        assert res.status_code == 404

    async def test_missing_name_returns_422(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/dashboards", json={}, headers=auth_headers(token)
        )
        assert res.status_code == 422

    async def test_no_auth_returns_401(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/dashboards")
        assert res.status_code == 401

    async def test_list_widget_count_is_correct(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token)
        dash_id = created["id"]
        await _create_widget(client, token, dash_id, title="W1")
        await _create_widget(client, token, dash_id, title="W2")
        res = await client.get(f"{BASE}/dashboards", headers=auth_headers(token))
        board = next(d for d in res.json()["data"] if d["id"] == dash_id)
        assert board["widget_count"] == 2


class TestDashboardRBAC:
    async def test_viewer_can_list_dashboards(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.get(f"{BASE}/dashboards", headers=auth_headers(viewer_token))
        assert res.status_code == 200

    async def test_viewer_can_get_dashboard(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        created = await _create_dashboard(client, owner_token)
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.get(
            f"{BASE}/dashboards/{created['id']}", headers=auth_headers(viewer_token)
        )
        assert res.status_code == 200

    async def test_viewer_cannot_create_dashboard(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.post(
            f"{BASE}/dashboards", json={"name": "Sneaky"}, headers=auth_headers(viewer_token)
        )
        assert res.status_code == 403

    async def test_viewer_cannot_delete_dashboard(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        created = await _create_dashboard(client, owner_token)
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.delete(
            f"{BASE}/dashboards/{created['id']}", headers=auth_headers(viewer_token)
        )
        assert res.status_code == 403

    async def test_analyst_cannot_delete_dashboard(self, client: AsyncClient) -> None:
        """Delete requires Admin+."""
        owner_token, _ = await _new_owner(client)
        created = await _create_dashboard(client, owner_token)
        analyst_token = await _invite_and_accept(client, owner_token, "analyst")
        res = await client.delete(
            f"{BASE}/dashboards/{created['id']}", headers=auth_headers(analyst_token)
        )
        assert res.status_code == 403

    async def test_admin_can_delete_dashboard(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        created = await _create_dashboard(client, owner_token)
        admin_token = await _invite_and_accept(client, owner_token, "admin")
        res = await client.delete(
            f"{BASE}/dashboards/{created['id']}", headers=auth_headers(admin_token)
        )
        assert res.status_code == 204

    async def test_analyst_can_create_dashboard(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        analyst_token = await _invite_and_accept(client, owner_token, "analyst")
        res = await client.post(
            f"{BASE}/dashboards", json={"name": "Analyst Board"}, headers=auth_headers(analyst_token)
        )
        assert res.status_code == 201


class TestDashboardOrgIsolation:
    async def test_cannot_get_other_orgs_dashboard(self, client: AsyncClient) -> None:
        token_a, _ = await _new_owner(client)
        token_b, _ = await _new_owner(client)
        created = await _create_dashboard(client, token_a)
        res = await client.get(
            f"{BASE}/dashboards/{created['id']}", headers=auth_headers(token_b)
        )
        assert res.status_code in (403, 404)

    async def test_list_only_returns_own_dashboards(self, client: AsyncClient) -> None:
        token_a, _ = await _new_owner(client)
        token_b, _ = await _new_owner(client)
        created_a = await _create_dashboard(client, token_a, name="Org A Board")
        res = await client.get(f"{BASE}/dashboards", headers=auth_headers(token_b))
        ids = [d["id"] for d in res.json()["data"]]
        assert created_a["id"] not in ids

    async def test_cannot_delete_other_orgs_dashboard(self, client: AsyncClient) -> None:
        token_a, _ = await _new_owner(client)
        token_b, _ = await _new_owner(client)
        created = await _create_dashboard(client, token_a)
        res = await client.delete(
            f"{BASE}/dashboards/{created['id']}", headers=auth_headers(token_b)
        )
        assert res.status_code in (403, 404)


# ── Dashboard Sharing ─────────────────────────────────────────────────────────

class TestDashboardSharing:
    async def test_enable_sharing_returns_share_url_and_token(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token)
        res = await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": True},
            headers=auth_headers(token),
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["share_token"]
        assert data["share_url"]
        assert data["share_token"] in data["share_url"]

    async def test_disable_sharing_returns_null_token(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token)
        await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": True},
            headers=auth_headers(token),
        )
        res = await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": False},
            headers=auth_headers(token),
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["share_token"] is None
        assert data["share_url"] is None

    async def test_shared_dashboard_accessible_without_auth(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token)
        share_res = await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": True},
            headers=auth_headers(token),
        )
        share_token = share_res.json()["data"]["share_token"]

        # No auth headers — should still work
        res = await client.get(f"{BASE}/dashboards/shared/{share_token}")
        assert res.status_code == 200
        assert res.json()["data"]["id"] == created["id"]

    async def test_disabled_shared_dashboard_returns_404(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token)
        share_res = await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": True},
            headers=auth_headers(token),
        )
        share_token = share_res.json()["data"]["share_token"]

        # Disable sharing
        await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": False},
            headers=auth_headers(token),
        )

        res = await client.get(f"{BASE}/dashboards/shared/{share_token}")
        assert res.status_code == 404

    async def test_invalid_share_token_returns_404(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/dashboards/shared/completely-fake-token")
        assert res.status_code == 404

    async def test_re_enable_generates_new_token(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        created = await _create_dashboard(client, token)
        r1 = await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": True},
            headers=auth_headers(token),
        )
        old_token = r1.json()["data"]["share_token"]

        await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": False},
            headers=auth_headers(token),
        )
        r2 = await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": True},
            headers=auth_headers(token),
        )
        new_token = r2.json()["data"]["share_token"]
        assert new_token != old_token

    async def test_viewer_cannot_share_dashboard(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        created = await _create_dashboard(client, owner_token)
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": True},
            headers=auth_headers(viewer_token),
        )
        assert res.status_code == 403

    async def test_analyst_can_share_dashboard(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        created = await _create_dashboard(client, owner_token)
        analyst_token = await _invite_and_accept(client, owner_token, "analyst")
        res = await client.post(
            f"{BASE}/dashboards/{created['id']}/share",
            json={"enabled": True},
            headers=auth_headers(analyst_token),
        )
        assert res.status_code == 200


# ── Widgets: CRUD ─────────────────────────────────────────────────────────────

class TestWidgetCRUD:
    async def test_create_line_chart_widget(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        res = await client.post(
            f"{BASE}/widgets",
            json={
                "dashboard_id": dash["id"],
                "title": "Line Widget",
                "widget_type": "line_chart",
                "time_range": "24h",
                "position": {"x": 0, "y": 0, "w": 6, "h": 4},
            },
            headers=auth_headers(token),
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["widget_type"] == "line_chart"
        assert data["title"] == "Line Widget"
        assert data["dashboard_id"] == dash["id"]

    async def test_create_all_widget_types(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        for wtype in ["line_chart", "bar_chart", "pie_chart", "kpi_card", "table"]:
            widget = await _create_widget(client, token, dash["id"], widget_type=wtype)
            assert widget["widget_type"] == wtype

    async def test_create_widget_with_saved_query(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        sq = await _create_saved_query(client, token)
        widget = await _create_widget(client, token, dash["id"], saved_query_id=sq["id"])
        assert widget["saved_query_id"] == sq["id"]

    async def test_get_widget_returns_correct_data(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        widget = await _create_widget(client, token, dash["id"], title="Fetch Me")
        res = await client.get(
            f"{BASE}/widgets/{widget['id']}", headers=auth_headers(token)
        )
        assert res.status_code == 200
        assert res.json()["data"]["title"] == "Fetch Me"

    async def test_update_widget_title_and_type(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        widget = await _create_widget(client, token, dash["id"])
        res = await client.put(
            f"{BASE}/widgets/{widget['id']}",
            json={"title": "Updated", "widget_type": "bar_chart"},
            headers=auth_headers(token),
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["title"] == "Updated"
        assert data["widget_type"] == "bar_chart"

    async def test_update_widget_position(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        widget = await _create_widget(client, token, dash["id"])
        res = await client.put(
            f"{BASE}/widgets/{widget['id']}",
            json={"position": {"x": 4, "y": 2, "w": 8, "h": 6}},
            headers=auth_headers(token),
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["position_x"] == 4
        assert data["position_y"] == 2
        assert data["width"] == 8
        assert data["height"] == 6

    async def test_delete_widget_returns_204(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        widget = await _create_widget(client, token, dash["id"])
        res = await client.delete(
            f"{BASE}/widgets/{widget['id']}", headers=auth_headers(token)
        )
        assert res.status_code == 204

    async def test_deleted_widget_not_in_dashboard(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        widget = await _create_widget(client, token, dash["id"])
        await client.delete(f"{BASE}/widgets/{widget['id']}", headers=auth_headers(token))
        res = await client.get(f"{BASE}/dashboards/{dash['id']}", headers=auth_headers(token))
        widget_ids = [w["id"] for w in res.json()["data"]["widgets"]]
        assert widget["id"] not in widget_ids

    async def test_get_nonexistent_widget_returns_404(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.get(f"{BASE}/widgets/{uuid.uuid4()}", headers=auth_headers(token))
        assert res.status_code == 404

    async def test_create_widget_on_other_orgs_dashboard_returns_404(self, client: AsyncClient) -> None:
        token_a, _ = await _new_owner(client)
        token_b, _ = await _new_owner(client)
        dash_a = await _create_dashboard(client, token_a)
        res = await client.post(
            f"{BASE}/widgets",
            json={
                "dashboard_id": dash_a["id"],
                "title": "Sneaky",
                "widget_type": "line_chart",
                "time_range": "24h",
                "position": {"x": 0, "y": 0, "w": 4, "h": 4},
            },
            headers=auth_headers(token_b),
        )
        assert res.status_code == 404

    async def test_create_widget_with_other_orgs_saved_query_returns_404(self, client: AsyncClient) -> None:
        token_a, _ = await _new_owner(client)
        token_b, _ = await _new_owner(client)
        dash_b = await _create_dashboard(client, token_b)
        sq_a = await _create_saved_query(client, token_a)
        res = await client.post(
            f"{BASE}/widgets",
            json={
                "dashboard_id": dash_b["id"],
                "saved_query_id": sq_a["id"],
                "title": "Cross-Org Widget",
                "widget_type": "line_chart",
                "time_range": "24h",
                "position": {"x": 0, "y": 0, "w": 4, "h": 4},
            },
            headers=auth_headers(token_b),
        )
        assert res.status_code == 404

    async def test_dashboard_shows_widgets_in_correct_order(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        await client.post(
            f"{BASE}/widgets",
            json={
                "dashboard_id": dash["id"], "title": "Second", "widget_type": "bar_chart",
                "time_range": "24h", "position": {"x": 6, "y": 2, "w": 6, "h": 4},
            },
            headers=auth_headers(token),
        )
        await client.post(
            f"{BASE}/widgets",
            json={
                "dashboard_id": dash["id"], "title": "First", "widget_type": "line_chart",
                "time_range": "24h", "position": {"x": 0, "y": 0, "w": 6, "h": 4},
            },
            headers=auth_headers(token),
        )
        res = await client.get(f"{BASE}/dashboards/{dash['id']}", headers=auth_headers(token))
        widgets = res.json()["data"]["widgets"]
        assert widgets[0]["title"] == "First"
        assert widgets[1]["title"] == "Second"

    async def test_missing_dashboard_id_returns_422(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        res = await client.post(
            f"{BASE}/widgets",
            json={"title": "No Dash", "widget_type": "bar_chart", "time_range": "24h",
                  "position": {"x": 0, "y": 0, "w": 4, "h": 4}},
            headers=auth_headers(token),
        )
        assert res.status_code == 422


class TestWidgetRBAC:
    async def test_viewer_can_read_widget(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, owner_token)
        widget = await _create_widget(client, owner_token, dash["id"])
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.get(
            f"{BASE}/widgets/{widget['id']}", headers=auth_headers(viewer_token)
        )
        assert res.status_code == 200

    async def test_viewer_cannot_create_widget(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, owner_token)
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.post(
            f"{BASE}/widgets",
            json={"dashboard_id": dash["id"], "title": "Bad", "widget_type": "bar_chart",
                  "time_range": "24h", "position": {"x": 0, "y": 0, "w": 4, "h": 4}},
            headers=auth_headers(viewer_token),
        )
        assert res.status_code == 403

    async def test_viewer_cannot_delete_widget(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, owner_token)
        widget = await _create_widget(client, owner_token, dash["id"])
        viewer_token = await _invite_and_accept(client, owner_token, "viewer")
        res = await client.delete(
            f"{BASE}/widgets/{widget['id']}", headers=auth_headers(viewer_token)
        )
        assert res.status_code == 403

    async def test_analyst_can_create_and_delete_widget(self, client: AsyncClient) -> None:
        owner_token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, owner_token)
        analyst_token = await _invite_and_accept(client, owner_token, "analyst")
        widget = await _create_widget(client, analyst_token, dash["id"])
        res = await client.delete(
            f"{BASE}/widgets/{widget['id']}", headers=auth_headers(analyst_token)
        )
        assert res.status_code == 204


# ── Query Result Shapes ───────────────────────────────────────────────────────

class TestQueryResult:
    async def test_widget_with_no_query_has_null_query_result(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        widget = await _create_widget(client, token, dash["id"])
        res = await client.get(f"{BASE}/widgets/{widget['id']}", headers=auth_headers(token))
        assert res.json()["data"]["query_result"] is None

    async def test_widget_with_query_has_query_result_shape(self, client: AsyncClient) -> None:
        import uuid as _uuid
        from datetime import UTC, datetime
        from app.core.database import AsyncSessionLocal
        from app.models.event import Event

        token, org_id_str = await _new_owner(client)
        org_id = _uuid.UUID(org_id_str)

        # Seed events
        async with AsyncSessionLocal() as db:
            db.add_all([
                Event(
                    organization_id=org_id,
                    event_name="page_view",
                    properties={},
                    timestamp=datetime.now(UTC),
                    source="api",
                )
                for _ in range(3)
            ])
            await db.commit()

        sq = await _create_saved_query(client, token, name="Page Views Query")
        dash = await _create_dashboard(client, token)
        widget = await _create_widget(client, token, dash["id"], saved_query_id=sq["id"])

        res = await client.get(f"{BASE}/widgets/{widget['id']}", headers=auth_headers(token))
        qr = res.json()["data"]["query_result"]
        assert qr is not None
        assert "data" in qr
        assert isinstance(qr["data"], list)
        assert "cached" in qr

    async def test_dashboard_widgets_include_query_results(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token, template_type="web_analytics")
        res = await client.get(f"{BASE}/dashboards/{dash['id']}", headers=auth_headers(token))
        widgets = res.json()["data"]["widgets"]
        # Template widgets all have saved queries attached
        for w in widgets:
            assert "query_result" in w
            assert w["query_result"] is not None or w["saved_query_id"] is not None


# ── Time Range Validation ─────────────────────────────────────────────────────

class TestTimeRanges:
    async def test_valid_time_ranges_accepted(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        for tr in ["1h", "6h", "24h", "7d", "30d"]:
            sq = await _create_saved_query(client, token, name=f"Query {tr}", time_range=tr)
            assert sq["query_config"]["time_range"] == tr

    async def test_widget_time_ranges(self, client: AsyncClient) -> None:
        token, _ = await _new_owner(client)
        dash = await _create_dashboard(client, token)
        for tr in ["1h", "6h", "24h", "7d", "30d"]:
            res = await client.post(
                f"{BASE}/widgets",
                json={
                    "dashboard_id": dash["id"], "title": f"Widget {tr}",
                    "widget_type": "line_chart", "time_range": tr,
                    "position": {"x": 0, "y": 0, "w": 4, "h": 4},
                },
                headers=auth_headers(token),
            )
            assert res.status_code == 201
            assert res.json()["data"]["time_range"] == tr


# ── Health Check (sanity) ─────────────────────────────────────────────────────

class TestHealthCheck:
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        res = await client.get(f"{BASE}/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
