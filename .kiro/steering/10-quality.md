# 10-quality.md — Code Quality, Testing & Standards

---

## Python Project Configuration

### pyproject.toml
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=70"

[tool.ruff]
target-version = "py311"
line-length = 88
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
]
ignore = ["E501"]   # line too long (handled by formatter)

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
disallow_untyped_defs = true
disallow_any_generics = true
warn_return_any = true
warn_unused_configs = true

[tool.coverage.run]
omit = ["tests/*", "alembic/*", "scripts/*"]
```

### Pre-commit Configuration (.pre-commit-config.yaml)
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: detect-private-key        # prevents accidental secret commits
      - id: check-added-large-files
```

### Install Pre-commit
```bash
pip install pre-commit
pre-commit install
# Now runs automatically before every git commit
```

---

## Testing Patterns

### conftest.py Setup
```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import get_db
from app.models.base import Base

# Test database (separate from dev DB)
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/test_wexa"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db(test_engine) -> AsyncSession:
    """Fresh DB session per test with rollback"""
    async with test_engine.begin() as conn:
        session = AsyncSession(bind=conn)
        yield session
        await session.rollback()

@pytest.fixture
async def client(db) -> AsyncClient:
    """Test HTTP client with DB override"""
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()

# Shared test data fixtures
@pytest.fixture
async def test_org(db):
    from app.repositories.organization_repo import OrganizationRepository
    repo = OrganizationRepository()
    return await repo.create(db, name="Test Org", slug="test-org")

@pytest.fixture
async def test_user(db, test_org):
    from app.services.auth_service import AuthService
    service = AuthService()
    user, _, _ = await service.signup(db, {
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User",
        "org_name": "Test Org"
    })
    return user

@pytest.fixture
async def auth_headers(client, test_user):
    """Returns headers with valid JWT"""
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### Test Examples
```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient

class TestSignup:
    async def test_signup_creates_user_and_org(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/signup", json={
            "email": "new@example.com",
            "password": "password123",
            "full_name": "New User",
            "org_name": "New Org"
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "new@example.com"
        assert data["org"]["name"] == "New Org"

    async def test_signup_duplicate_email_returns_409(self, client, test_user):
        response = await client.post("/api/v1/auth/signup", json={
            "email": "test@example.com",  # already exists
            "password": "password123",
            "full_name": "Duplicate",
            "org_name": "Duplicate Org"
        })
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"

class TestRolePermissions:
    async def test_viewer_cannot_create_dashboard(self, client, viewer_headers):
        response = await client.post(
            "/api/v1/dashboards",
            json={"name": "Test Dashboard"},
            headers=viewer_headers
        )
        assert response.status_code == 403

    async def test_analyst_can_create_dashboard(self, client, analyst_headers):
        response = await client.post(
            "/api/v1/dashboards",
            json={"name": "Test Dashboard"},
            headers=analyst_headers
        )
        assert response.status_code == 201
```

---

## Git Strategy

### Branch Naming
```
dev        → main development branch
main       → production (auto deploys)

Feature branches (optional for large features):
feature/auth-system
feature/data-ingestion
fix/login-cookie-bug
```

### Commit Message Format
```
type(scope): short description

Types:
feat     → new feature
fix      → bug fix
chore    → maintenance, dependency updates
docs     → documentation
test     → adding tests
refactor → code change without new feature
style    → formatting, no logic change

Examples:
feat(auth): add JWT refresh token rotation
fix(ingestion): handle malformed CSV rows gracefully
chore(deps): update SQLAlchemy to 2.0.36
test(dashboard): add widget CRUD tests
docs: update README with deployment steps
```

### Git Tag Per Phase
```bash
git tag -a phase-1-complete -m "Architecture setup complete"
git tag -a phase-2-complete -m "Auth & Multi-tenancy complete"
git tag -a phase-3-complete -m "Data Ingestion complete"
git tag -a phase-4-complete -m "Dashboards & Widgets complete"
git push origin --tags
```

### .gitignore Critical Entries
```gitignore
# Never commit these
.env
.env.local
.env.production
*.env

# Python
__pycache__/
*.pyc
venv/
.venv/
*.egg-info/

# Node
node_modules/
.next/

# Testing
.coverage
htmlcov/
.pytest_cache/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
```

---

## README Structure
```markdown
# Wexa Analytics Platform

> Real-time analytics and reporting platform built as a technical assessment
> for Wexa AI Senior Full Stack Engineer position.

## 🔗 Live Demo
- Frontend: https://wexa-analytics.vercel.app
- API Docs: https://api.wexa-analytics.railway.app/docs
- Test credentials:
  - Owner: owner@acme.com / password123
  - Viewer: viewer@acme.com / password123

## 🏗️ Architecture
[Brief description of layers + diagram]

## ⚡ Features Implemented
### Must Have (Completed)
- [x] JWT Auth with refresh tokens
- [x] Multi-tenancy with role-based access
- [x] Data ingestion API
- [x] Custom dashboards with widgets

### Should Have (Completed)
- [x] Threshold-based alerts
- [ ] WebSocket real-time updates (in progress)

## 🚀 Local Setup
[Step by step instructions]

## 🏛️ Design Decisions
- Why FastAPI over Django: [reason]
- Why Neon over self-hosted PostgreSQL: [reason]
- Why Upstash over Docker Redis: [reason]

## 📁 Project Structure
[Folder tree with explanations]

## 🧪 Running Tests
[Commands]

## 🔧 Environment Variables
[Table of all variables]
```

---

## Code Review Checklist (Self Review Before Each Commit)
```
Backend:
[ ] All functions have type hints
[ ] All async functions use await
[ ] No sync SQLAlchemy patterns
[ ] All DB queries filter by org_id
[ ] All endpoints have error handling
[ ] No hardcoded values (use settings)
[ ] Tests written for new code
[ ] structlog used (not print statements)

Frontend:
[ ] No any TypeScript types
[ ] Loading states implemented
[ ] Error states implemented
[ ] Optimistic updates where appropriate
[ ] No hardcoded API URLs (use env vars)
[ ] Responsive design checked
```
