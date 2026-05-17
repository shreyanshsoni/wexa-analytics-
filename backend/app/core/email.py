"""Async email sending via Resend API."""
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

_RESEND_URL = "https://api.resend.com/emails"


async def _send_invite_via_resend(
    *,
    to_email: str,
    inviter_name: str,
    org_name: str,
    invite_token: str,
    role: str,
) -> None:
    """Low-level: POST to Resend API. Raises on network/API errors."""
    if not settings.RESEND_API_KEY:
        logger.warning("email_skipped", reason="RESEND_API_KEY not set", to=to_email)
        return

    invite_url = f"{settings.FRONTEND_URL}/invite/{invite_token}"

    html_body = f"""
    <div style="font-family: Inter, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px;">
      <h2 style="color: #111827; margin-bottom: 8px;">You've been invited to join {org_name}</h2>
      <p style="color: #6b7280; font-size: 15px;">
        <strong>{inviter_name}</strong> has invited you to join <strong>{org_name}</strong>
        on Wexa Analytics as a <strong>{role}</strong>.
      </p>
      <a href="{invite_url}"
         style="display: inline-block; margin-top: 24px; padding: 12px 24px;
                background: #2563eb; color: #fff; border-radius: 6px;
                text-decoration: none; font-weight: 600; font-size: 15px;">
        Accept Invitation
      </a>
      <p style="margin-top: 24px; color: #9ca3af; font-size: 13px;">
        This link expires in 7 days. If you did not expect this invitation, you can ignore it.
      </p>
      <hr style="border: none; border-top: 1px solid #e5e7eb; margin-top: 32px;" />
      <p style="color: #9ca3af; font-size: 12px;">Or copy: {invite_url}</p>
    </div>
    """

    payload = {
        "from": f"Wexa Analytics <{settings.EMAIL_FROM}>",
        "to": [to_email],
        "subject": f"You've been invited to join {org_name} on Wexa Analytics",
        "html": html_body,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            _RESEND_URL,
            json=payload,
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
        )
        if response.status_code >= 400:
            logger.error(
                "email_send_failed",
                to=to_email,
                status=response.status_code,
                body=response.text,
            )
        else:
            logger.info("email_sent", to=to_email, org=org_name)


async def send_invite_email(
    *,
    to_email: str,
    inviter_name: str,
    org_name: str,
    invite_token: str,
    role: str,
) -> None:
    """Public wrapper: send invite email, swallowing all errors so callers never fail."""
    try:
        await _send_invite_via_resend(
            to_email=to_email,
            inviter_name=inviter_name,
            org_name=org_name,
            invite_token=invite_token,
            role=role,
        )
    except Exception as exc:
        logger.error("email_send_error", to=to_email, error=str(exc))
