import asyncio
import os
import sys

# Ensure project root (/app) is on sys.path when invoked as `python scripts/seed.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from scripts.seed_leads_data import SEED_LEADS


def _get_engine():
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_async_engine(url, echo=False)


async def _insert_leads(session_factory):
    from app.models.lead import Lead

    inserted = 0
    skipped = 0

    async with session_factory() as session:
        for lead_data in SEED_LEADS:
            result = await session.execute(
                select(Lead).where(Lead.email == lead_data["email"])
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                print(f"  SKIP  {lead_data['email']} (already exists, id={existing.id})")
                skipped += 1
                continue

            lead = Lead(**lead_data)
            session.add(lead)
            await session.flush()
            await session.refresh(lead)
            inserted += 1
            print(f"  INSERT {lead_data['email']} → id={lead.id}")

        await session.commit()

    return inserted, skipped


async def main():
    from app.models.lead import Lead

    engine = _get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    print("\n=== Inserting leads ===")
    inserted, skipped = await _insert_leads(session_factory)

    async with session_factory() as session:
        total_leads = (await session.execute(select(func.count()).select_from(Lead))).scalar()

    print("\n" + "=" * 50)
    print("SEED SUMMARY")
    print("=" * 50)
    print(f"  Total leads in database : {total_leads}")
    print(f"  Leads inserted this run : {inserted}")
    print(f"  Leads skipped this run  : {skipped}")
    print("=" * 50)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
