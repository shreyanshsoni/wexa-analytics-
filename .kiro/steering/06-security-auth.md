# 06-security-auth.md — Security, Authentication & Permissions

---

## JWT Implementation

### Token Structure
```python
# Access Token Payload
{
    "sub": str(user_id),       # subject = user UUID
    "org_id": str(org_id),     # current organization
    "role": "owner|admin|analyst|viewer",
    "type": "access",
    "exp": unix_timestamp,     # 15 minutes from now
    "iat": unix_timestamp,     # issued at
    "jti": str(uuid4()),       # unique token ID
}

# Refresh Token (not a JWT — random secure string)
# Stored as: SHA-256 hash in DB
# Sent as: HTTP-only, Secure, SameSite=Lax cookie
```

### JWT Security Settings
```python
# app/core/security.py
SECRET_KEY = settings.SECRET_KEY   # min 32 chars, random
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Cookie settings for refresh token
COOKIE_NAME = "refresh_token"
COOKIE_HTTPONLY = True
COOKIE_SECURE = True              # HTTPS only in production
COOKIE_SAMESITE = "lax"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds
```

### Password Hashing
```python
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12           # cost factor — not too low, not too high
)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

### API Key Hashing
```python
import hashlib
import secrets
import base64

def generate_api_key() -> tuple[str, str]:
    """Returns (raw_key, key_hash)"""
    random_bytes = secrets.token_bytes(32)
    raw_key = "wxa_" + base64.urlsafe_b64encode(random_bytes).decode().rstrip("=")
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12]   # "wxa_" + first 8 chars
    return raw_key, key_hash, key_prefix

def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
```

---

## FastAPI Dependencies (Dependency Injection)

### Authentication Dependencies
```python
# app/core/dependencies.py

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate JWT token"""
    # Decode JWT
    # Get user from DB
    # Check user is active
    # Return user

async def get_current_org(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, Organization, Membership]:
    """Get current user with their org membership"""
    # Get membership for user's current org
    # Return user, org, membership tuple

# Role-specific dependencies
async def require_owner(membership = Depends(get_current_org)):
    if membership.role != "owner":
        raise ForbiddenError("Owner role required")

async def require_admin(membership = Depends(get_current_org)):
    if membership.role not in ["owner", "admin"]:
        raise ForbiddenError("Admin role required")

async def require_analyst(membership = Depends(get_current_org)):
    if membership.role not in ["owner", "admin", "analyst"]:
        raise ForbiddenError("Analyst role required")

# Any authenticated member (including viewer)
async def require_member(membership = Depends(get_current_org)):
    return membership  # just being a member is enough
```

### API Key Dependencies
```python
async def get_org_by_api_key(
    api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    """Validate API key and return associated org"""
    key_hash = hash_api_key(api_key)
    api_key_record = await api_key_repo.get_by_hash(db, key_hash)
    if not api_key_record or api_key_record.revoked_at:
        raise UnauthorizedError("Invalid API key")
    # Update last_used_at
    await api_key_repo.update_last_used(db, api_key_record.id)
    return api_key_record.organization
```

---

## Permission Matrix (Every Endpoint × Every Role)

### Auth Endpoints
| Endpoint | Owner | Admin | Analyst | Viewer | Public |
|---|---|---|---|---|---|
| POST /auth/signup | - | - | - | - | ✅ |
| POST /auth/login | - | - | - | - | ✅ |
| POST /auth/refresh | ✅ | ✅ | ✅ | ✅ | - |
| POST /auth/logout | ✅ | ✅ | ✅ | ✅ | - |

### Organization Endpoints
| Endpoint | Owner | Admin | Analyst | Viewer |
|---|---|---|---|---|
| GET /organizations/me | ✅ | ✅ | ✅ | ✅ |
| PUT /organizations/me | ✅ | ❌ | ❌ | ❌ |
| DELETE /organizations/me | ✅ | ❌ | ❌ | ❌ |
| GET /organizations/members | ✅ | ✅ | ✅ | ✅ |
| POST /organizations/invite | ✅ | ✅ | ❌ | ❌ |
| DELETE /organizations/members/{id} | ✅ | ✅* | ❌ | ❌ |
| PUT /organizations/members/{id}/role | ✅ | ✅* | ❌ | ❌ |

*Admin cannot modify Owner's role or remove Owner

### API Key Endpoints
| Endpoint | Owner | Admin | Analyst | Viewer |
|---|---|---|---|---|
| GET /api-keys | ✅ | ✅ | ❌ | ❌ |
| POST /api-keys | ✅ | ✅ | ❌ | ❌ |
| POST /api-keys/{id}/revoke | ✅ | ✅ | ❌ | ❌ |
| POST /api-keys/{id}/rotate | ✅ | ✅ | ❌ | ❌ |

### Ingestion Endpoints (API Key Auth)
| Endpoint | API Key Required |
|---|---|
| POST /ingest/events | ✅ |
| POST /ingest/events/batch | ✅ |
| POST /ingest/csv | ✅ JWT (Analyst+) |
| POST /ingest/webhook/{id} | Webhook signature |

### Dashboard Endpoints
| Endpoint | Owner | Admin | Analyst | Viewer | Public |
|---|---|---|---|---|---|
| GET /dashboards | ✅ | ✅ | ✅ | ✅ | - |
| POST /dashboards | ✅ | ✅ | ✅ | ❌ | - |
| GET /dashboards/{id} | ✅ | ✅ | ✅ | ✅ | - |
| PUT /dashboards/{id} | ✅ | ✅ | ✅ | ❌ | - |
| DELETE /dashboards/{id} | ✅ | ✅ | ❌ | ❌ | - |
| POST /dashboards/{id}/share | ✅ | ✅ | ✅ | ❌ | - |
| GET /dashboards/shared/{token} | - | - | - | - | ✅ |

### Widget Endpoints
| Endpoint | Owner | Admin | Analyst | Viewer |
|---|---|---|---|---|
| GET /widgets (by dashboard) | ✅ | ✅ | ✅ | ✅ |
| POST /widgets | ✅ | ✅ | ✅ | ❌ |
| PUT /widgets/{id} | ✅ | ✅ | ✅ | ❌ |
| DELETE /widgets/{id} | ✅ | ✅ | ✅ | ❌ |

### Alert Endpoints
| Endpoint | Owner | Admin | Analyst | Viewer |
|---|---|---|---|---|
| GET /alerts | ✅ | ✅ | ✅ | ✅ |
| POST /alerts | ✅ | ✅ | ✅ | ❌ |
| PUT /alerts/{id} | ✅ | ✅ | ✅ | ❌ |
| DELETE /alerts/{id} | ✅ | ✅ | ❌ | ❌ |
| POST /alerts/{id}/mute | ✅ | ✅ | ✅ | ❌ |
| POST /alerts/{id}/snooze | ✅ | ✅ | ✅ | ❌ |
| GET /alerts/{id}/history | ✅ | ✅ | ✅ | ✅ |

---

## Organization Data Isolation Rules

### EVERY DB query MUST include org_id filter
```python
# ✅ CORRECT — always filter by org_id
async def get_dashboards(db: AsyncSession, org_id: UUID) -> list[Dashboard]:
    result = await db.execute(
        select(Dashboard)
        .where(Dashboard.org_id == org_id)
        .where(Dashboard.deleted_at.is_(None))
    )
    return result.scalars().all()

# ❌ WRONG — missing org_id filter (data leak across orgs)
async def get_dashboards(db: AsyncSession) -> list[Dashboard]:
    result = await db.execute(select(Dashboard))
    return result.scalars().all()
```

### Ownership Verification
```python
# Before any update/delete — verify resource belongs to org
async def verify_dashboard_ownership(
    db: AsyncSession,
    dashboard_id: UUID,
    org_id: UUID
) -> Dashboard:
    dashboard = await dashboard_repo.get_by_id(db, dashboard_id)
    if not dashboard or dashboard.org_id != org_id:
        raise NotFoundError("Dashboard not found")  # NOT 403 — don't reveal existence
    return dashboard
```

---

## CORS Configuration
```python
# app/core/middleware.py
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "http://localhost:3000",        # dev frontend
    settings.FRONTEND_URL,          # production frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,         # REQUIRED for cookies (refresh token)
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
```

---

## Rate Limiting
```python
# Using slowapi + Upstash Redis
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL
)

# On ingestion endpoints:
@router.post("/events")
@limiter.limit("1000/minute")   # per IP (API key rate limiting in service layer)
async def ingest_event(...):
    ...

# Per-org rate limiting in service layer (Redis counter)
async def check_org_rate_limit(redis, org_id: UUID):
    key = f"rate_limit:org:{org_id}:events"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)  # 1 minute window
    if count > 1000:
        raise RateLimitError("Org rate limit exceeded: 1000 events/minute")
```
