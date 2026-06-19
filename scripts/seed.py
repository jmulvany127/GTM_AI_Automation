import asyncio
import os
import time

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from scripts.seed_leads_data import SEED_LEADS
from scripts.seed_transcripts_data import SEED_TRANSCRIPTS

BASE_URL = "http://localhost:8000"


def _get_engine():
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_async_engine(url, echo=False)


async def _insert_leads(session_factory):
    from app.models.lead import Lead

    inserted = []
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
                inserted.append(None)
                continue

            lead = Lead(**lead_data)
            session.add(lead)
            await session.flush()
            await session.refresh(lead)
            inserted.append(lead.id)
            print(f"  INSERT {lead_data['email']} → id={lead.id}")

        await session.commit()

    total_inserted = sum(1 for x in inserted if x is not None)
    print(f"\nLeads: {total_inserted} inserted, {skipped} skipped.\n")
    return inserted


async def _run_pipeline(lead_id: int, client: httpx.AsyncClient):
    steps = [
        ("analyze", f"/leads/{lead_id}/analyze"),
        ("generate-outreach", f"/leads/{lead_id}/generate-outreach"),
        ("run-agent", f"/leads/{lead_id}/run-agent"),
    ]
    for name, path in steps:
        try:
            resp = await client.post(f"{BASE_URL}{path}", timeout=60.0)
            if resp.status_code in (200, 201):
                print(f"    [{lead_id}] {name} → OK ({resp.status_code})")
            else:
                print(f"    [{lead_id}] {name} → HTTP {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:
            print(f"    [{lead_id}] {name} → ERROR: {exc}")


async def _submit_transcripts(inserted_ids: list, client: httpx.AsyncClient):
    submitted = 0
    failed = 0
    for transcript in SEED_TRANSCRIPTS:
        idx = transcript["lead_index"]
        if idx >= len(inserted_ids) or inserted_ids[idx] is None:
            print(f"  SKIP transcript '{transcript['title']}' (lead at index {idx} not inserted)")
            failed += 1
            continue

        lead_id = inserted_ids[idx]
        payload = {
            "lead_id": lead_id,
            "title": transcript["title"],
            "description": transcript["description"],
            "transcript": transcript["transcript"],
        }
        try:
            resp = await client.post(f"{BASE_URL}/call-notes/analyze", json=payload, timeout=60.0)
            if resp.status_code in (200, 201):
                print(f"  OK   '{transcript['title']}' (lead_id={lead_id})")
                submitted += 1
            else:
                print(f"  FAIL '{transcript['title']}' → HTTP {resp.status_code}: {resp.text[:120]}")
                failed += 1
        except Exception as exc:
            print(f"  FAIL '{transcript['title']}' → ERROR: {exc}")
            failed += 1

    print(f"\nTranscripts: {submitted} submitted, {failed} failed.\n")
    return submitted


async def _print_summary(session_factory):
    from app.models.lead import Lead
    from app.models.analysis import LeadAnalysis
    from app.models.outreach import OutreachMessage
    from app.models.call_analysis import CallAnalysis

    async with session_factory() as session:
        total_leads = (await session.execute(select(func.count()).select_from(Lead))).scalar()
        total_analyses = (await session.execute(select(func.count()).select_from(LeadAnalysis))).scalar()
        total_outreach = (await session.execute(select(func.count()).select_from(OutreachMessage))).scalar()
        total_calls = (await session.execute(select(func.count()).select_from(CallAnalysis))).scalar()

    print("=" * 50)
    print("SEED SUMMARY")
    print("=" * 50)
    print(f"  Total leads in database     : {total_leads}")
    print(f"  Total analyses created      : {total_analyses}")
    print(f"  Total outreach messages     : {total_outreach}")
    print(f"  Total call analyses         : {total_calls}")
    print("=" * 50)


async def main():
    engine = _get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    print("\n=== STEP 1: Inserting leads ===")
    inserted_ids = await _insert_leads(session_factory)

    new_lead_ids = [lid for lid in inserted_ids if lid is not None]
    print(f"=== STEP 2: Running pipeline on {len(new_lead_ids)} new leads ===")
    async with httpx.AsyncClient() as client:
        for lead_id in new_lead_ids:
            print(f"  Processing lead {lead_id}...")
            await _run_pipeline(lead_id, client)
            time.sleep(1)

        print("\n=== STEP 3: Submitting call transcripts ===")
        await _submit_transcripts(inserted_ids, client)

    print("=== STEP 4: Final summary ===")
    await _print_summary(session_factory)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
