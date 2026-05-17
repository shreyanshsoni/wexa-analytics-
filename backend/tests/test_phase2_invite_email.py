"""Phase 2 — Invite email regression tests via Resend."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, signup_user, unique_email

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE = "/api/v1"


# ── Integration: invite API sends email ───────────────────────────────────────

class TestInviteEmailSent:
    async def test_invite_triggers_email_with_correct_args(
        self, client: AsyncClient, mock_send_invite_email: AsyncMock
    ) -> None:
        """Sending an invite must call send_invite_email with the right params."""
        mock_send_invite_email.reset_mock()

        signup = await signup_user(client, full_name="Alice Owner")
        token = signup["data"]["access_token"]
        org_name = signup["data"]["org"]["name"]
        invitee = unique_email()

        res = await client.post(
            f"{BASE}/organizations/invite",
            headers=auth_headers(token),
            json={"email": invitee, "role": "analyst"},
        )
        assert res.status_code == 201
        mock_send_invite_email.assert_called_once()

        kw = mock_send_invite_email.call_args.kwargs
        assert kw["to_email"] == invitee
        assert kw["inviter_name"] == "Alice Owner"
        assert kw["org_name"] == org_name
        assert kw["role"] == "analyst"
        assert len(kw["invite_token"]) > 10

    async def test_invite_token_matches_db_record(
        self, client: AsyncClient, mock_send_invite_email: AsyncMock
    ) -> None:
        """Token passed to email must match what is stored in the DB."""
        mock_send_invite_email.reset_mock()

        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        invitee = unique_email()

        await client.post(
            f"{BASE}/organizations/invite",
            headers=auth_headers(token),
            json={"email": invitee, "role": "viewer"},
        )

        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.invite import Invite

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Invite).where(Invite.email == invitee))
            invite = result.scalar_one_or_none()

        assert invite is not None
        kw = mock_send_invite_email.call_args.kwargs
        assert kw["invite_token"] == invite.token

    async def test_email_failure_does_not_break_invite(
        self, client: AsyncClient, mock_send_invite_email: AsyncMock
    ) -> None:
        """If email sending raises, the invite 201 must still be returned."""
        mock_send_invite_email.side_effect = Exception("Resend is down")
        try:
            signup = await signup_user(client)
            token = signup["data"]["access_token"]
            invitee = unique_email()

            res = await client.post(
                f"{BASE}/organizations/invite",
                headers=auth_headers(token),
                json={"email": invitee, "role": "viewer"},
            )
            assert res.status_code == 201
            data = res.json()["data"]
            assert data["invite_id"]
            assert data["expires_at"]
        finally:
            mock_send_invite_email.side_effect = None

    async def test_duplicate_invite_returns_409_no_second_email(
        self, client: AsyncClient, mock_send_invite_email: AsyncMock
    ) -> None:
        """Second invite to same email must 409 and must NOT trigger another email."""
        mock_send_invite_email.reset_mock()

        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        invitee = unique_email()

        res1 = await client.post(
            f"{BASE}/organizations/invite",
            headers=auth_headers(token),
            json={"email": invitee, "role": "viewer"},
        )
        assert res1.status_code == 201
        assert mock_send_invite_email.call_count == 1

        mock_send_invite_email.reset_mock()
        res2 = await client.post(
            f"{BASE}/organizations/invite",
            headers=auth_headers(token),
            json={"email": invitee, "role": "viewer"},
        )
        assert res2.status_code == 409
        mock_send_invite_email.assert_not_called()

    async def test_two_distinct_invites_each_send_email(
        self, client: AsyncClient, mock_send_invite_email: AsyncMock
    ) -> None:
        """Two different invitees → two separate email calls."""
        mock_send_invite_email.reset_mock()

        signup = await signup_user(client)
        token = signup["data"]["access_token"]
        email_a, email_b = unique_email(), unique_email()

        await client.post(
            f"{BASE}/organizations/invite",
            headers=auth_headers(token),
            json={"email": email_a, "role": "viewer"},
        )
        await client.post(
            f"{BASE}/organizations/invite",
            headers=auth_headers(token),
            json={"email": email_b, "role": "analyst"},
        )

        assert mock_send_invite_email.call_count == 2
        called_to = [c.kwargs["to_email"] for c in mock_send_invite_email.call_args_list]
        assert email_a in called_to
        assert email_b in called_to


# ── Unit: _send_invite_via_resend (real HTTP logic, no session mock) ──────────

class TestSendInviteEmailFunction:
    """Tests for the low-level Resend HTTP call — uses _send_invite_via_resend directly
    so the session-scoped mock on send_invite_email does not interfere."""

    async def test_posts_to_resend_with_correct_payload(self) -> None:
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_instance

            with patch("app.core.email.settings") as s:
                s.RESEND_API_KEY = "re_test_key"
                s.EMAIL_FROM = "onboarding@resend.dev"
                s.FRONTEND_URL = "http://localhost:3000"

                from app.core.email import _send_invite_via_resend
                await _send_invite_via_resend(
                    to_email="invitee@example.com",
                    inviter_name="Alice Owner",
                    org_name="Acme Corp",
                    invite_token="tok123",
                    role="analyst",
                )

        mock_instance.post.assert_called_once()
        payload = mock_instance.post.call_args.kwargs["json"]
        assert payload["to"] == ["invitee@example.com"]
        assert "Acme Corp" in payload["subject"]
        assert "tok123" in payload["html"]
        assert "analyst" in payload["html"]
        assert "Alice Owner" in payload["html"]
        assert mock_instance.post.call_args.kwargs["headers"]["Authorization"] == "Bearer re_test_key"

    async def test_invite_link_uses_frontend_url(self) -> None:
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_instance

            with patch("app.core.email.settings") as s:
                s.RESEND_API_KEY = "re_test"
                s.EMAIL_FROM = "onboarding@resend.dev"
                s.FRONTEND_URL = "https://app.wexa.ai"

                from app.core.email import _send_invite_via_resend
                await _send_invite_via_resend(
                    to_email="user@example.com",
                    inviter_name="Bob",
                    org_name="Beta Inc",
                    invite_token="xyz789",
                    role="viewer",
                )

        payload = mock_instance.post.call_args.kwargs["json"]
        assert "https://app.wexa.ai/invite/xyz789" in payload["html"]

    async def test_skips_http_when_api_key_empty(self) -> None:
        """No HTTP call when RESEND_API_KEY is blank."""
        with patch("httpx.AsyncClient") as mock_cls:
            with patch("app.core.email.settings") as s:
                s.RESEND_API_KEY = ""

                from app.core.email import _send_invite_via_resend
                await _send_invite_via_resend(
                    to_email="user@example.com",
                    inviter_name="Bob",
                    org_name="Beta Inc",
                    invite_token="tok",
                    role="viewer",
                )

        mock_cls.assert_not_called()

    async def test_resend_error_response_logged_not_raised(self) -> None:
        """4xx from Resend API must log an error but not raise an exception."""
        mock_response = AsyncMock()
        mock_response.status_code = 422
        mock_response.text = '{"name":"missing_required_field"}'

        with patch("httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_instance

            with patch("app.core.email.settings") as s:
                s.RESEND_API_KEY = "re_test"
                s.EMAIL_FROM = "onboarding@resend.dev"
                s.FRONTEND_URL = "http://localhost:3000"

                from app.core.email import _send_invite_via_resend
                # Must not raise even though Resend returned 422
                await _send_invite_via_resend(
                    to_email="user@example.com",
                    inviter_name="Bob",
                    org_name="Beta Inc",
                    invite_token="tok",
                    role="viewer",
                )
