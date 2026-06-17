from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/roi")
async def get_roi_metrics(db: AsyncSession = Depends(get_db)):
    return await metrics_service.get_roi_metrics(db)
