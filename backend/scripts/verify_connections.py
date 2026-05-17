"""
Run this script to verify all external connections are working correctly.
Usage: python scripts/verify_connections.py
"""
import asyncio
import ssl
import sys

import certifi


async def check_database() -> bool:
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal

    print("Checking PostgreSQL (Neon)...")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar_one()
            print(f"  ✅ Connected — {version[:50]}")

            result = await session.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            ))
            tables = [row[0] for row in result.fetchall()]
            expected = {
                "alert_history", "alerts", "api_keys", "dashboards",
                "events", "invites", "memberships", "organizations",
                "refresh_tokens", "reports", "saved_queries", "users", "widgets",
            }
            missing = expected - set(tables)
            if missing:
                print(f"  ❌ Missing tables: {missing}")
                return False
            print(f"  ✅ All {len(tables)} tables present: {', '.join(sorted(tables))}")
            return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


async def check_redis() -> bool:
    from app.core.redis import get_redis, close_redis

    print("Checking Redis (Upstash)...")
    try:
        redis = await get_redis()
        await redis.ping()
        await redis.set("wexa:healthcheck", "ok", ex=10)
        val = await redis.get("wexa:healthcheck")
        assert val == "ok"
        await close_redis()
        print("  ✅ Connected — ping OK, set/get OK")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def check_ssl() -> bool:
    print("Checking SSL configuration...")
    ctx = ssl.create_default_context(cafile=certifi.where())
    # Verify cert_reqs is CERT_REQUIRED (not CERT_NONE)
    if ctx.verify_mode != ssl.CERT_REQUIRED:
        print(f"  ❌ SSL verify mode is {ctx.verify_mode}, expected CERT_REQUIRED")
        return False
    print(f"  ✅ certifi CA bundle: {certifi.where()}")
    print(f"  ✅ SSL verify mode: CERT_REQUIRED")
    return True


async def main() -> None:
    print("\n=== Wexa Analytics — Connection Verification ===\n")

    ssl_ok = check_ssl()
    print()
    db_ok = await check_database()
    print()
    redis_ok = await check_redis()

    print("\n=== Summary ===")
    print(f"  SSL (certifi):  {'✅ PASS' if ssl_ok else '❌ FAIL'}")
    print(f"  PostgreSQL:     {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"  Redis:          {'✅ PASS' if redis_ok else '❌ FAIL'}")

    if all([ssl_ok, db_ok, redis_ok]):
        print("\n✅ All checks passed — safe to proceed to Phase 2\n")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed — fix before proceeding\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
