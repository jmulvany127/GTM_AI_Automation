from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(payload: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead = Lead(**payload.model_dump())
    db.add(lead)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    await db.refresh(lead)
    return lead


@router.get("", response_model=list[LeadRead])
async def list_leads(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead))
    return result.scalars().all()
