from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, get_db
from app.routers.leads import router as leads_router
from app.routers.analysis import router as analysis_router
from app.routers.outreach import router as outreach_router
from app.routers.workflow import router as workflow_router
from app.routers.hubspot import router as hubspot_router
from app.routers.metrics import router as metrics_router
from app.routers.dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="GTM AI System", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(leads_router)
app.include_router(analysis_router)
app.include_router(outreach_router)
app.include_router(workflow_router)
app.include_router(hubspot_router)
app.include_router(metrics_router)
app.include_router(dashboard_router)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(e)},
        )
