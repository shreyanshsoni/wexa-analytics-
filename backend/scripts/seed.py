"""Database seeding script for development."""
import asyncio

import structlog

logger = structlog.get_logger()


async def seed() -> None:
    logger.info("seed_start")
    # Seed data will be added in Phase 2 after auth is implemented
    logger.info("seed_complete")


if __name__ == "__main__":
    asyncio.run(seed())
