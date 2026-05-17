# 05-database.md — Database Schema, Migrations & Seeding

---

## Complete Database Schema

### Base Model (all tables inherit this)
```python
class Base(AsyncAttrs, DeclarativeBase):
    pass

class TimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, default=None)
```

### Table: users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),           -- nullable for OAuth users
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
```

### Table: organizations
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,    -- URL-safe org identifier
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_organizations_slug ON organizations(slug) WHERE deleted_at IS NULL;
```

### Table: memberships
```sql
CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    org_id UUID NOT NULL REFERENCES organizations(id),
    role VARCHAR(50) NOT NULL CHECK (role IN ('owner', 'admin', 'analyst', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(user_id, org_id)
);
CREATE INDEX idx_memberships_user ON memberships(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_memberships_org ON memberships(org_id) WHERE deleted_at IS NULL;
```

### Table: invites
```sql
CREATE TABLE invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    invited_by UUID NOT NULL REFERENCES users(id),
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_invites_token ON invites(token_hash);
CREATE INDEX idx_invites_email ON invites(email);
```

### Table: refresh_tokens
```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
```

### Table: api_keys
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    created_by UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,      -- first 8 chars for display
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_org ON api_keys(org_id);
```

### Table: events (TIME-SERIES OPTIMIZED)
```sql
CREATE TABLE events (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    properties JSONB NOT NULL DEFAULT '{}',
    source VARCHAR(50) NOT NULL DEFAULT 'api', -- api|csv|webhook
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE events_2024_01 PARTITION OF events
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE events_2024_02 PARTITION OF events
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- etc... create for current + next 3 months at minimum

-- Indexes on EACH partition (automatically inherited)
CREATE INDEX idx_events_org_time ON events(org_id, timestamp DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_events_name ON events(org_id, event_name, timestamp DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_events_properties ON events USING GIN(properties)
    WHERE deleted_at IS NULL;
```

### Table: dashboards
```sql
CREATE TABLE dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    created_by UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    share_token VARCHAR(255) UNIQUE,      -- null = not shared publicly
    is_template BOOLEAN DEFAULT false,
    template_type VARCHAR(50),            -- web_analytics|sales|devops
    auto_refresh_interval VARCHAR(10),    -- 30s|1m|5m|null
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_dashboards_org ON dashboards(org_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_dashboards_share ON dashboards(share_token) WHERE share_token IS NOT NULL;
```

### Table: saved_queries
```sql
CREATE TABLE saved_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    event_name VARCHAR(255),
    aggregation VARCHAR(50) NOT NULL DEFAULT 'count',
    group_by VARCHAR(50) NOT NULL DEFAULT 'hour',
    filters JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
```

### Table: widgets
```sql
CREATE TABLE widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID NOT NULL REFERENCES dashboards(id),
    org_id UUID NOT NULL REFERENCES organizations(id),
    saved_query_id UUID REFERENCES saved_queries(id),
    title VARCHAR(255) NOT NULL,
    widget_type VARCHAR(50) NOT NULL CHECK (
        widget_type IN ('line_chart', 'bar_chart', 'pie_chart', 'kpi_card', 'table')
    ),
    time_range VARCHAR(20) NOT NULL DEFAULT '24h',
    position JSONB NOT NULL DEFAULT '{"x":0,"y":0,"w":6,"h":4}',
    config JSONB NOT NULL DEFAULT '{}',   -- widget-specific config
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_widgets_dashboard ON widgets(dashboard_id) WHERE deleted_at IS NULL;
```

### Table: alerts
```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    created_by UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    saved_query_id UUID REFERENCES saved_queries(id),
    condition VARCHAR(10) NOT NULL CHECK (condition IN ('gt','lt','gte','lte','eq')),
    threshold DECIMAL(20, 4) NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 5,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    muted_until TIMESTAMPTZ,
    notification_channels JSONB NOT NULL DEFAULT '["in_app"]',
    notification_config JSONB NOT NULL DEFAULT '{}',  -- webhook URLs etc
    last_evaluated_at TIMESTAMPTZ,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
```

### Table: alert_history
```sql
CREATE TABLE alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id),
    org_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL,          -- triggered|resolved
    triggered_value DECIMAL(20, 4),
    threshold DECIMAL(20, 4),
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_alert_history_alert ON alert_history(alert_id);
```

### Table: reports
```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    dashboard_id UUID NOT NULL REFERENCES dashboards(id),
    created_by UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    schedule VARCHAR(20) NOT NULL,        -- daily|weekly|monthly
    cron_expression VARCHAR(100) NOT NULL,
    recipients JSONB NOT NULL DEFAULT '[]',
    format VARCHAR(10) NOT NULL DEFAULT 'pdf',
    last_generated_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
```

---

## SQLAlchemy Async Patterns

### Session Factory Setup
```python
# app/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,         # verify connection before use
    pool_recycle=3600,          # recycle connections after 1 hour
    echo=settings.ENVIRONMENT == "development",
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,     # IMPORTANT: prevent lazy loading issues
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Correct Async Query Patterns
```python
# ✅ CORRECT — SQLAlchemy 2.0 async
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()

# ❌ WRONG — Do not use these patterns
session.query(User).filter_by(email=email).first()  # sync pattern
await session.execute("SELECT * FROM users")         # raw SQL without text()
```

---

## Alembic Migration Commands
```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "description of change"

# Run migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

### Async Alembic Setup (env.py)
```python
# alembic/env.py — must use async runner
from sqlalchemy.ext.asyncio import async_engine_from_config

def run_migrations_online():
    connectable = async_engine_from_config(...)

    async def do_run_migrations(connection):
        await connection.run_sync(do_run_migrations_sync)

    asyncio.run(do_run_migrations(connectable))
```

---

## Seeding Strategy

### Seed Data Structure
```
Seed Order (respect foreign key dependencies):
1. Organizations (3 orgs)
2. Users (2-3 per org, one of each role)
3. Memberships (link users to orgs)
4. API Keys (2 per org)
5. Saved Queries (5 per org)
6. Dashboards (3 per org, including templates)
7. Widgets (4-6 per dashboard)
8. Events (10,000 per org, spread over last 30 days)
9. Alerts (3 per org)
10. Alert History (some triggered alerts)
```

### Running Seeds
```bash
# From backend directory
python scripts/seed.py

# Reset and re-seed
python scripts/seed.py --reset

# Minimal seed (faster, for testing)
python scripts/seed.py --minimal
```

### Seed Credentials (Dev Only)
```
Org 1: Acme Corp
  Owner:   owner@acme.com / password123
  Admin:   admin@acme.com / password123
  Analyst: analyst@acme.com / password123
  Viewer:  viewer@acme.com / password123

Org 2: Beta Inc
  Owner: owner@beta.com / password123

API Key (Acme): wxa_test_acme_key_001 (shown only once in seed output)
```

### ⚠️ Never Seed In Production
```python
# scripts/seed.py — always check environment
if settings.ENVIRONMENT == "production":
    raise RuntimeError("Cannot run seed script in production!")
```

### Idempotent Seeding
```python
# Always use get_or_create pattern
async def get_or_create_user(db, email, **kwargs):
    user = await user_repo.get_by_email(db, email)
    if not user:
        user = await user_repo.create(db, email=email, **kwargs)
    return user
```

---

## Soft Delete Pattern
```python
# Never hard delete — always set deleted_at
# All queries must filter: WHERE deleted_at IS NULL

# In repository base:
async def soft_delete(self, db: AsyncSession, id: UUID) -> None:
    await db.execute(
        update(self.model)
        .where(self.model.id == id)
        .values(deleted_at=func.now())
    )
    await db.commit()

# In all queries — ALWAYS include:
.where(Model.deleted_at.is_(None))
```
