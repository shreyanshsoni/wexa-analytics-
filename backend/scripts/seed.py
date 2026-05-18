"""
Demo seed script — wipes the DB and creates realistic data for all 4 roles.

Run:  make seed   (or: cd backend && python scripts/seed.py)

Credentials after seeding
─────────────────────────
  owner@wexa.demo    / Demo1234!   → Owner
  admin@wexa.demo    / Demo1234!   → Admin
  analyst@wexa.demo  / Demo1234!   → Analyst
  viewer@wexa.demo   / Demo1234!   → Viewer
"""
import asyncio
import hashlib
import random
import secrets
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# ── path bootstrap ──────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import generate_api_key, hash_password
from app.models.api_key import ApiKey
from app.models.dashboard import Dashboard
from app.models.event import Event
from app.models.membership import MemberRole, Membership
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.saved_query import SavedQuery
from app.models.user import User
from app.models.widget import Widget

logger = structlog.get_logger()

# ── config ──────────────────────────────────────────────────────────────────
PASSWORD = "Demo1234!"
ORG_NAME = "Acme Corp"
ORG_SLUG = "acme-corp"

USERS = [
    {"email": "owner@wexa.demo",   "full_name": "Alex Owner",   "role": MemberRole.OWNER},
    {"email": "admin@wexa.demo",   "full_name": "Sam Admin",    "role": MemberRole.ADMIN},
    {"email": "analyst@wexa.demo", "full_name": "Taylor Analyst","role": MemberRole.ANALYST},
    {"email": "viewer@wexa.demo",  "full_name": "Jordan Viewer", "role": MemberRole.VIEWER},
]

# Tables in safe truncation order (children before parents)
_TRUNCATE_ORDER = [
    "widgets", "saved_queries", "dashboards",
    "alert_history", "alerts",
    "api_keys", "refresh_tokens", "invites",
    "memberships", "events",
    "users", "organizations",
]


# ── helpers ─────────────────────────────────────────────────────────────────

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _rand_ts(days_ago_max: int = 30, days_ago_min: int = 0) -> datetime:
    """Random timestamp within the past N days, weighted toward business hours."""
    days_back = random.uniform(days_ago_min, days_ago_max)
    base = datetime.now(UTC) - timedelta(days=days_back)
    # Bias toward 9 AM–7 PM
    hour = random.choices(
        range(24),
        weights=[1,1,1,1,1,1,1,2,4,6,8,8,7,7,8,8,7,6,5,4,3,2,1,1],
        k=1,
    )[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return base.replace(hour=hour, minute=minute, second=second, microsecond=0)


async def _wipe(db: AsyncSession) -> None:
    logger.info("wipe_start")
    for table in _TRUNCATE_ORDER:
        await db.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
    await db.commit()
    logger.info("wipe_done")


# ── seeding ─────────────────────────────────────────────────────────────────

async def _create_org_and_users(db: AsyncSession) -> tuple[Organization, dict[str, User]]:
    org = Organization(id=uuid.uuid4(), name=ORG_NAME, slug=ORG_SLUG)
    db.add(org)
    await db.flush()

    users: dict[str, User] = {}
    for u in USERS:
        user = User(
            id=uuid.uuid4(),
            email=u["email"],
            full_name=u["full_name"],
            hashed_password=hash_password(PASSWORD),
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        membership = Membership(
            id=uuid.uuid4(),
            user_id=user.id,
            organization_id=org.id,
            role=u["role"],
        )
        db.add(membership)
        users[u["role"]] = user

    await db.flush()
    logger.info("users_created", count=len(users))
    return org, users


async def _create_api_keys(db: AsyncSession, org: Organization, owner: User) -> list[str]:
    raw_keys = []
    for name in ["Production Key", "Development Key"]:
        raw, hashed = generate_api_key()
        key = ApiKey(
            id=uuid.uuid4(),
            organization_id=org.id,
            created_by_id=owner.id,
            name=name,
            key_hash=hashed,
            key_prefix=raw[:12],
            is_active=True,
        )
        db.add(key)
        raw_keys.append(raw)
    await db.flush()
    logger.info("api_keys_created", count=len(raw_keys))
    return raw_keys


async def _create_events(db: AsyncSession, org: Organization) -> None:
    """Create ~2500 events spread over 30 days with realistic distributions."""
    events: list[Event] = []

    # Web traffic events — most frequent
    for _ in range(900):
        events.append(Event(
            organization_id=org.id,
            event_name="page_view",
            properties={
                "url": random.choice(["/", "/pricing", "/about", "/docs", "/blog", "/signup", "/login"]),
                "referrer": random.choice(["google", "direct", "twitter", "linkedin", "github", ""]),
                "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"]),
                "country": random.choice(["US", "GB", "DE", "IN", "CA", "AU", "FR"]),
            },
            timestamp=_rand_ts(30),
            source="api",
        ))

    # Button clicks
    for _ in range(420):
        events.append(Event(
            organization_id=org.id,
            event_name="button_click",
            properties={
                "label": random.choice(["Get Started", "Sign Up Free", "Watch Demo", "Contact Sales", "Learn More"]),
                "page": random.choice(["/", "/pricing", "/about"]),
            },
            timestamp=_rand_ts(30),
            source="api",
        ))

    # Signups
    for _ in range(180):
        events.append(Event(
            organization_id=org.id,
            event_name="sign_up",
            properties={
                "plan": random.choice(["free", "pro", "enterprise"]),
                "source": random.choice(["organic", "paid", "referral"]),
            },
            timestamp=_rand_ts(30),
            source="api",
        ))

    # Purchases / revenue events
    for _ in range(95):
        events.append(Event(
            organization_id=org.id,
            event_name="purchase",
            properties={
                "plan": random.choice(["pro", "enterprise"]),
                "amount": random.choice([29, 49, 99, 199, 499]),
                "currency": "USD",
            },
            timestamp=_rand_ts(30),
            source="api",
        ))

    # Checkout attempts
    for _ in range(210):
        events.append(Event(
            organization_id=org.id,
            event_name="checkout",
            properties={
                "step": random.choice(["started", "payment_info", "review", "completed", "abandoned"]),
                "plan": random.choice(["pro", "enterprise"]),
            },
            timestamp=_rand_ts(30),
            source="api",
        ))

    # API requests (DevOps template)
    for _ in range(480):
        events.append(Event(
            organization_id=org.id,
            event_name="request",
            properties={
                "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
                "endpoint": random.choice(["/api/events", "/api/dashboards", "/api/auth", "/api/ingest"]),
                "status": random.choices([200, 201, 400, 401, 404, 500], weights=[60,20,5,5,7,3])[0],
                "latency_ms": random.randint(12, 850),
            },
            timestamp=_rand_ts(30),
            source="api",
        ))

    # Errors (DevOps template)
    for _ in range(85):
        events.append(Event(
            organization_id=org.id,
            event_name="error",
            properties={
                "type": random.choice(["TypeError", "DatabaseError", "AuthError", "ValidationError", "TimeoutError"]),
                "severity": random.choice(["warning", "error", "critical"]),
                "service": random.choice(["api", "worker", "ingestion"]),
            },
            timestamp=_rand_ts(30),
            source="api",
        ))

    # CSV-sourced events (last 7 days — simulates a CSV upload)
    for _ in range(130):
        events.append(Event(
            organization_id=org.id,
            event_name="page_view",
            properties={"url": "/imported-page", "source": "csv_import"},
            timestamp=_rand_ts(7),
            source="csv",
        ))

    db.add_all(events)
    await db.flush()
    logger.info("events_created", count=len(events))


async def _create_saved_queries(
    db: AsyncSession, org: Organization
) -> dict[str, SavedQuery]:
    queries_config = [
        {
            "name": "Page Views Over Time",
            "config": {"event_name": "page_view", "aggregation": "count", "group_by": "hour", "filters": [], "time_range": "24h"},
        },
        {
            "name": "Daily Signups",
            "config": {"event_name": "sign_up", "aggregation": "count", "group_by": "day", "filters": [], "time_range": "30d"},
        },
        {
            "name": "Purchase Revenue",
            "config": {"event_name": "purchase", "aggregation": "count", "group_by": "day", "filters": [], "time_range": "30d"},
        },
        {
            "name": "Error Rate",
            "config": {"event_name": "error", "aggregation": "count", "group_by": "hour", "filters": [], "time_range": "24h"},
        },
        {
            "name": "Button Clicks (7 days)",
            "config": {"event_name": "button_click", "aggregation": "count", "group_by": "day", "filters": [], "time_range": "7d"},
        },
        {
            "name": "API Request Volume",
            "config": {"event_name": "request", "aggregation": "count", "group_by": "hour", "filters": [], "time_range": "24h"},
        },
        {
            "name": "Weekly Checkouts",
            "config": {"event_name": "checkout", "aggregation": "count", "group_by": "day", "filters": [], "time_range": "7d"},
        },
        {
            "name": "Total Page Views (30 days)",
            "config": {"event_name": "page_view", "aggregation": "count", "group_by": "day", "filters": [], "time_range": "30d"},
        },
    ]

    saved: dict[str, SavedQuery] = {}
    for q in queries_config:
        sq = SavedQuery(
            id=uuid.uuid4(),
            organization_id=org.id,
            name=q["name"],
            query_config=q["config"],
        )
        db.add(sq)
        saved[q["name"]] = sq

    await db.flush()
    logger.info("saved_queries_created", count=len(saved))
    return saved


async def _create_dashboards(
    db: AsyncSession,
    org: Organization,
    owner: User,
    queries: dict[str, SavedQuery],
) -> None:
    # ── 1. Custom "Executive Overview" dashboard ────────────────────────────
    dash_exec = Dashboard(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by_id=owner.id,
        name="Executive Overview",
        description="Top-level KPIs and trends across all channels",
        is_public=True,
        share_token=secrets.token_urlsafe(32),
        refresh_interval=300,  # 5m
    )
    db.add(dash_exec)
    await db.flush()

    _add_widget(db, dash_exec.id, queries["Page Views Over Time"].id,      "Page Views (24h)", "line_chart", 0, 0, 8, 4, "24h")
    _add_widget(db, dash_exec.id, queries["Daily Signups"].id,             "New Signups",      "kpi_card",  8, 0, 4, 2, "7d")
    _add_widget(db, dash_exec.id, queries["Purchase Revenue"].id,          "Purchases",        "kpi_card",  8, 2, 4, 2, "30d")
    _add_widget(db, dash_exec.id, queries["Button Clicks (7 days)"].id,    "Button Clicks",    "bar_chart", 0, 4, 6, 4, "7d")
    _add_widget(db, dash_exec.id, queries["Weekly Checkouts"].id,          "Checkouts",        "pie_chart", 6, 4, 6, 4, "7d")

    # ── 2. Web Analytics template ───────────────────────────────────────────
    dash_web = Dashboard(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by_id=owner.id,
        name="Web Analytics",
        description="Page views, signups, and user engagement",
        template_type="web_analytics",
        refresh_interval=60,  # 1m
    )
    db.add(dash_web)
    await db.flush()

    _add_widget(db, dash_web.id, queries["Total Page Views (30 days)"].id, "Page Views (30d)", "line_chart", 0, 0, 8, 4, "30d")
    _add_widget(db, dash_web.id, queries["Daily Signups"].id,              "Signups",           "kpi_card",  8, 0, 4, 2, "30d")
    _add_widget(db, dash_web.id, queries["Button Clicks (7 days)"].id,    "Clicks",            "bar_chart", 0, 4, 12, 4, "7d")

    # ── 3. DevOps template ──────────────────────────────────────────────────
    dash_ops = Dashboard(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by_id=owner.id,
        name="DevOps & Reliability",
        description="API request volume, error rate, latency",
        template_type="devops",
        refresh_interval=30,  # 30s
    )
    db.add(dash_ops)
    await db.flush()

    _add_widget(db, dash_ops.id, queries["API Request Volume"].id, "Request Volume (24h)", "line_chart", 0, 0, 8, 4, "24h")
    _add_widget(db, dash_ops.id, queries["Error Rate"].id,         "Error Rate (24h)",     "bar_chart",  0, 4, 6, 4, "24h")
    _add_widget(db, dash_ops.id, queries["Error Rate"].id,         "Errors (KPI)",         "kpi_card",   8, 0, 4, 2, "24h")
    _add_widget(db, dash_ops.id, queries["API Request Volume"].id, "Requests (KPI)",       "kpi_card",   8, 2, 4, 2, "24h")

    # ── 4. Sales dashboard ──────────────────────────────────────────────────
    dash_sales = Dashboard(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by_id=owner.id,
        name="Sales & Revenue",
        description="Purchases, checkouts, and conversion funnel",
        template_type="sales",
    )
    db.add(dash_sales)
    await db.flush()

    _add_widget(db, dash_sales.id, queries["Purchase Revenue"].id,  "Purchases (30d)",  "line_chart", 0, 0, 8, 4, "30d")
    _add_widget(db, dash_sales.id, queries["Purchase Revenue"].id,  "Total Purchases",  "kpi_card",   8, 0, 4, 2, "30d")
    _add_widget(db, dash_sales.id, queries["Weekly Checkouts"].id,  "Checkouts",        "kpi_card",   8, 2, 4, 2, "7d")
    _add_widget(db, dash_sales.id, queries["Daily Signups"].id,     "Signups (30d)",    "bar_chart",  0, 4, 6, 4, "30d")
    _add_widget(db, dash_sales.id, queries["Weekly Checkouts"].id,  "Checkout Funnel",  "pie_chart",  6, 4, 6, 4, "7d")

    await db.flush()
    logger.info("dashboards_created", count=4)


def _add_widget(
    db: AsyncSession,
    dashboard_id: uuid.UUID,
    saved_query_id: uuid.UUID,
    title: str,
    widget_type: str,
    x: int, y: int, w: int, h: int,
    time_range: str = "24h",
) -> None:
    db.add(Widget(
        id=uuid.uuid4(),
        dashboard_id=dashboard_id,
        saved_query_id=saved_query_id,
        title=title,
        widget_type=widget_type,
        config={"time_range": time_range},
        position_x=x,
        position_y=y,
        width=w,
        height=h,
    ))


# ── main ────────────────────────────────────────────────────────────────────

async def seed() -> None:
    async with AsyncSessionLocal() as db:
        await _wipe(db)
        org, users = await _create_org_and_users(db)
        api_keys = await _create_api_keys(db, org, users[MemberRole.OWNER])
        await _create_events(db, org)
        queries = await _create_saved_queries(db, org)
        await _create_dashboards(db, org, users[MemberRole.OWNER], queries)
        await db.commit()

    print("\n" + "═" * 56)
    print("  SEED COMPLETE — Demo credentials")
    print("═" * 56)
    print(f"  {'Role':<12}  Email")
    print(f"  {'────':<12}  ─────────────────────")
    for u in USERS:
        print(f"  {u['role']:<12}  {u['email']}")
    print(f"\n  Password (all accounts): {PASSWORD}")
    print(f"\n  API Keys (use as X-API-Key header):")
    for i, key in enumerate(api_keys, 1):
        print(f"    Key {i}: {key}")
    print("═" * 56 + "\n")


if __name__ == "__main__":
    asyncio.run(seed())
