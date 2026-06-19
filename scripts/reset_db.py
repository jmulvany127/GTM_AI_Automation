import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


def _get_engine():
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_async_engine(url, echo=False)


TABLES_IN_ORDER = [
    "call_analysis",
    "automation_metrics",
    "outreach_messages",
    "lead_analysis",
    "crm_sync_logs",
    "leads",
]


async def main():
    confirm = input(
        "This will delete ALL rows from the seeded tables. Type 'yes' to confirm: "
    ).strip()
    if confirm != "yes":
        print("Aborted.")
        return

    engine = _get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        for table in TABLES_IN_ORDER:
            await session.execute(text(f"DELETE FROM {table}"))
            print(f"  Cleared: {table}")
        await session.commit()

    await engine.dispose()
    print("\nDatabase reset complete.")


if __name__ == "__main__":
    asyncio.run(main())
