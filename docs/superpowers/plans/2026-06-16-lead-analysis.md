# Lead Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `POST /leads/{lead_id}/analyze` endpoint that calls Claude Haiku via the Anthropic SDK, stores the result in a `lead_analysis` table, updates lead status to `"analyzed"`, and returns structured scoring data.

**Architecture:** The router owns all DB reads and writes. `ai_service.analyze_lead()` is a pure async function that receives a `Lead` object, calls the Anthropic API, and returns a plain dict — it never touches the database. This boundary keeps each layer independently unit-testable.

**Tech Stack:** FastAPI (async), SQLAlchemy 2.0 (async mapped columns), Pydantic v2, Anthropic Python SDK (`AsyncAnthropic`), Alembic, pytest with asyncio_mode=auto.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `app/config.py` | Modify | Add `ANTHROPIC_API_KEY` setting |
| `requirements.txt` | Modify | Add `anthropic>=0.25.0` |
| `.env.example` | Modify | Document `ANTHROPIC_API_KEY` |
| `tests/conftest.py` | Modify | Set `ANTHROPIC_API_KEY` env var for all tests |
| `tests/test_config.py` | Modify | Update Settings instantiation to include new key |
| `app/models/analysis.py` | Create | `LeadAnalysis` SQLAlchemy model |
| `app/models/__init__.py` | Modify | Import `LeadAnalysis` so Alembic autogenerate sees it |
| `tests/test_analysis_model.py` | Create | Model column and FK tests |
| `app/schemas/analysis.py` | Create | `LeadAnalysisCreate` and `LeadAnalysisRead` Pydantic schemas |
| `tests/test_analysis_schemas.py` | Create | Schema validation tests |
| `app/services/ai_service.py` | Create | `analyze_lead(lead)` — Anthropic API call, retry, fallback |
| `tests/test_analysis_service.py` | Create | Unit tests for the AI service (mocked Anthropic) |
| `app/routers/analysis.py` | Create | `POST /leads/{lead_id}/analyze` router |
| `app/main.py` | Modify | Register analysis router |
| `tests/test_analysis.py` | Create | Endpoint tests (200, 404) |
| `alembic/env.py` | Modify | Import models so autogenerate detects `lead_analysis` table |
| `alembic/versions/<hash>_add_lead_analysis_table.py` | Generate | Alembic migration |

---

## Task 1: Config, Dependencies, and Test Baseline

**Files:**
- Modify: `app/config.py`
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `tests/conftest.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1.1: Add `ANTHROPIC_API_KEY` to Settings**

Open `app/config.py` and replace the entire file with:

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    DATABASE_URL: str
    APP_ENV: str = "development"
    ANTHROPIC_API_KEY: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 1.2: Add `anthropic` to requirements.txt**

Open `requirements.txt` and add one line at the end:

```
anthropic>=0.25.0
```

- [ ] **Step 1.3: Document the key in .env.example**

Open `.env.example` and append:

```
ANTHROPIC_API_KEY=your_key_here
```

- [ ] **Step 1.4: Add `ANTHROPIC_API_KEY` to conftest.py**

`conftest.py` is loaded by pytest before any test module is imported. Adding the key here ensures all tests that trigger `get_settings()` work without a real API key.

Open `tests/conftest.py` and replace the entire file with:

```python
import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    from app.database import get_db

    async def _override_get_db():
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=None)
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def client_db_fail():
    from app.main import app
    from app.database import get_db

    async def _override_get_db_fail():
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Connection refused"))
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db_fail
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

- [ ] **Step 1.5: Update test_config.py to pass `ANTHROPIC_API_KEY`**

`Settings` now requires `ANTHROPIC_API_KEY`. The existing tests that construct `Settings` directly must pass it. Open `tests/test_config.py` and replace the entire file with:

```python
from app.config import Settings, get_settings


def test_settings_app_env_default():
    s = Settings(DATABASE_URL="postgresql+asyncpg://test:test@localhost/testdb", ANTHROPIC_API_KEY="test")
    assert s.APP_ENV == "development"


def test_settings_accepts_database_url():
    url = "postgresql+asyncpg://user:pass@localhost/mydb"
    s = Settings(DATABASE_URL=url, ANTHROPIC_API_KEY="test")
    assert s.DATABASE_URL == url


def test_get_settings_returns_singleton():
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    get_settings.cache_clear()
```

- [ ] **Step 1.6: Run the existing test suite to confirm no regressions**

```bash
pytest tests/ -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 1.7: Commit**

```bash
git add app/config.py requirements.txt .env.example tests/conftest.py tests/test_config.py
git commit -m "chore: add ANTHROPIC_API_KEY config and anthropic dependency"
```

---

## Task 2: LeadAnalysis SQLAlchemy Model

**Files:**
- Create: `app/models/analysis.py`
- Modify: `app/models/__init__.py`
- Create: `tests/test_analysis_model.py`

- [ ] **Step 2.1: Write the failing model test**

Create `tests/test_analysis_model.py`:

```python
from app.models.analysis import LeadAnalysis


def test_lead_analysis_tablename():
    assert LeadAnalysis.__tablename__ == "lead_analysis"


def test_lead_analysis_columns():
    col_names = {c.name for c in LeadAnalysis.__table__.columns}
    assert col_names == {
        "id", "lead_id", "company_summary", "persona_type",
        "pain_points", "buying_signals", "objections",
        "fit_score", "urgency_score", "overall_score",
        "recommended_action", "confidence_score", "raw_ai_json", "created_at",
    }


def test_lead_analysis_has_foreign_key_to_leads():
    fk_targets = {fk.target_fullname for fk in LeadAnalysis.__table__.foreign_keys}
    assert "leads.id" in fk_targets


def test_lead_analysis_defaults_to_none():
    analysis = LeadAnalysis(lead_id=1)
    assert analysis.company_summary is None
    assert analysis.fit_score is None
    assert analysis.confidence_score is None
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
pytest tests/test_analysis_model.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.models.analysis'`

- [ ] **Step 2.3: Create the LeadAnalysis model**

Create `app/models/analysis.py`:

```python
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class LeadAnalysis(Base):
    __tablename__ = "lead_analysis"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"), nullable=False)
    company_summary: Mapped[str | None] = mapped_column(Text, default=None)
    persona_type: Mapped[str | None] = mapped_column(String(100), default=None)
    pain_points: Mapped[str | None] = mapped_column(Text, default=None)
    buying_signals: Mapped[str | None] = mapped_column(Text, default=None)
    objections: Mapped[str | None] = mapped_column(Text, default=None)
    fit_score: Mapped[int | None] = mapped_column(Integer, default=None)
    urgency_score: Mapped[int | None] = mapped_column(Integer, default=None)
    overall_score: Mapped[int | None] = mapped_column(Integer, default=None)
    recommended_action: Mapped[str | None] = mapped_column(String(100), default=None)
    confidence_score: Mapped[float | None] = mapped_column(Float, default=None)
    raw_ai_json: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- [ ] **Step 2.4: Import LeadAnalysis in app/models/__init__.py**

Open `app/models/__init__.py` and replace the entire file:

```python
from app.models.lead import Lead
from app.models.analysis import LeadAnalysis

__all__ = ["Lead", "LeadAnalysis"]
```

- [ ] **Step 2.5: Run test to verify it passes**

```bash
pytest tests/test_analysis_model.py -v
```

Expected: 4 tests pass.

- [ ] **Step 2.6: Commit**

```bash
git add app/models/analysis.py app/models/__init__.py tests/test_analysis_model.py
git commit -m "feat: add LeadAnalysis SQLAlchemy model"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `app/schemas/analysis.py`
- Create: `tests/test_analysis_schemas.py`

- [ ] **Step 3.1: Write the failing schema test**

Create `tests/test_analysis_schemas.py`:

```python
from datetime import datetime
from unittest.mock import MagicMock
from app.schemas.analysis import LeadAnalysisCreate, LeadAnalysisRead


def test_lead_analysis_create_all_fields_optional():
    schema = LeadAnalysisCreate()
    assert schema.company_summary is None
    assert schema.fit_score is None
    assert schema.confidence_score is None
    assert schema.raw_ai_json is None


def test_lead_analysis_create_accepts_all_fields():
    schema = LeadAnalysisCreate(
        company_summary="A SaaS company",
        persona_type="Champion",
        pain_points="Manual processes",
        buying_signals="Requested demo",
        objections="Budget concerns",
        fit_score=75,
        urgency_score=60,
        overall_score=70,
        recommended_action="Schedule call",
        confidence_score=0.8,
        raw_ai_json='{"fit_score": 75}',
    )
    assert schema.fit_score == 75
    assert schema.confidence_score == 0.8


def test_lead_analysis_read_from_orm_object():
    obj = MagicMock()
    obj.id = 1
    obj.lead_id = 42
    obj.company_summary = "A SaaS company"
    obj.persona_type = "Champion"
    obj.pain_points = "Manual processes"
    obj.buying_signals = "Requested demo"
    obj.objections = "Budget"
    obj.fit_score = 75
    obj.urgency_score = 60
    obj.overall_score = 70
    obj.recommended_action = "Schedule call"
    obj.confidence_score = 0.8
    obj.raw_ai_json = '{"fit_score": 75}'
    obj.created_at = datetime(2026, 6, 16, 12, 0, 0)

    result = LeadAnalysisRead.model_validate(obj)
    assert result.id == 1
    assert result.lead_id == 42
    assert result.fit_score == 75
    assert result.confidence_score == 0.8
    assert result.created_at == datetime(2026, 6, 16, 12, 0, 0)
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
pytest tests/test_analysis_schemas.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.schemas.analysis'`

- [ ] **Step 3.3: Create the schemas**

Create `app/schemas/analysis.py`:

```python
from datetime import datetime
from pydantic import BaseModel


class LeadAnalysisCreate(BaseModel):
    company_summary: str | None = None
    persona_type: str | None = None
    pain_points: str | None = None
    buying_signals: str | None = None
    objections: str | None = None
    fit_score: int | None = None
    urgency_score: int | None = None
    overall_score: int | None = None
    recommended_action: str | None = None
    confidence_score: float | None = None
    raw_ai_json: str | None = None


class LeadAnalysisRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int
    company_summary: str | None
    persona_type: str | None
    pain_points: str | None
    buying_signals: str | None
    objections: str | None
    fit_score: int | None
    urgency_score: int | None
    overall_score: int | None
    recommended_action: str | None
    confidence_score: float | None
    raw_ai_json: str | None
    created_at: datetime
```

- [ ] **Step 3.4: Run test to verify it passes**

```bash
pytest tests/test_analysis_schemas.py -v
```

Expected: 3 tests pass.

- [ ] **Step 3.5: Commit**

```bash
git add app/schemas/analysis.py tests/test_analysis_schemas.py
git commit -m "feat: add LeadAnalysis Pydantic schemas"
```

---

## Task 4: AI Service

**Files:**
- Create: `app/services/ai_service.py`
- Create: `tests/test_analysis_service.py`

- [ ] **Step 4.1: Write the failing service tests**

Create `tests/test_analysis_service.py`:

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_service import analyze_lead


def _make_lead(**kwargs):
    defaults = dict(
        first_name="Jane", last_name="Smith",
        company="Acme Corp", job_title="VP Sales",
        company_website="acme.com", source="LinkedIn",
        notes="Interested in automation",
    )
    defaults.update(kwargs)
    lead = MagicMock()
    for k, v in defaults.items():
        setattr(lead, k, v)
    return lead


def _mock_anthropic_response(text: str):
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


_VALID_JSON_TEXT = json.dumps({
    "company_summary": "A sales enablement company",
    "persona_type": "Champion",
    "pain_points": "Manual sales processes",
    "buying_signals": "Requested a demo",
    "objections": "Budget concerns",
    "fit_score": 80,
    "urgency_score": 60,
    "overall_score": 70,
    "recommended_action": "Schedule discovery call",
    "confidence_score": 0.85,
})


async def test_analyze_lead_returns_correct_structure():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(_VALID_JSON_TEXT)
        )
        result = await analyze_lead(_make_lead())

    assert result["fit_score"] == 80
    assert result["urgency_score"] == 60
    assert result["overall_score"] == 70
    assert result["confidence_score"] == 0.85
    assert result["persona_type"] == "Champion"
    assert result["raw_ai_json"] == _VALID_JSON_TEXT


async def test_analyze_lead_malformed_json_returns_fallback():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response("not valid json {{{{")
        )
        result = await analyze_lead(_make_lead())

    assert result["fit_score"] == 0
    assert result["urgency_score"] == 0
    assert result["overall_score"] == 0
    assert result["confidence_score"] == 0.0
    assert result["company_summary"] is None
    assert result["raw_ai_json"] == "not valid json {{{{"


async def test_analyze_lead_exception_retries_once_then_fallback():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(side_effect=Exception("API unavailable"))

        result = await analyze_lead(_make_lead())

    assert instance.messages.create.call_count == 2
    assert result["fit_score"] == 0
    assert result["confidence_score"] == 0.0


async def test_score_fields_are_integers_in_range():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(_VALID_JSON_TEXT)
        )
        result = await analyze_lead(_make_lead())

    assert isinstance(result["fit_score"], int)
    assert isinstance(result["urgency_score"], int)
    assert isinstance(result["overall_score"], int)
    assert 0 <= result["fit_score"] <= 100
    assert 0 <= result["urgency_score"] <= 100
    assert 0 <= result["overall_score"] <= 100


async def test_confidence_score_is_float_in_range():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(_VALID_JSON_TEXT)
        )
        result = await analyze_lead(_make_lead())

    assert isinstance(result["confidence_score"], float)
    assert 0.0 <= result["confidence_score"] <= 1.0
```

- [ ] **Step 4.2: Run test to verify it fails**

```bash
pytest tests/test_analysis_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.ai_service'`

- [ ] **Step 4.3: Create the AI service**

Create `app/services/ai_service.py`:

```python
import json
from anthropic import AsyncAnthropic
from app.config import get_settings

_SYSTEM_PROMPT = (
    "You are a B2B sales intelligence assistant. Analyze the lead information provided "
    "and return ONLY a valid JSON object with no explanation, preamble, or markdown fences.\n\n"
    "Use cautious, conservative language. Do not invent specific facts about the company. "
    "When signal is weak, default to low scores.\n\n"
    "Return exactly this JSON structure:\n"
    '{\n'
    '  "company_summary": "<brief factual description based only on provided info, or null>",\n'
    '  "persona_type": "<buyer persona type, or null>",\n'
    '  "pain_points": "<likely pain points based on role/industry, or null>",\n'
    '  "buying_signals": "<positive signals from notes/source, or null>",\n'
    '  "objections": "<likely objections, or null>",\n'
    '  "fit_score": <integer 0-100>,\n'
    '  "urgency_score": <integer 0-100>,\n'
    '  "overall_score": <integer 0-100>,\n'
    '  "recommended_action": "<next best action string, or null>",\n'
    '  "confidence_score": <float 0.0-1.0>\n'
    "}\n\n"
    "All score fields are required integers. confidence_score is a required float. "
    "Return only JSON, nothing else."
)

_FALLBACK: dict = {
    "company_summary": None,
    "persona_type": None,
    "pain_points": None,
    "buying_signals": None,
    "objections": None,
    "fit_score": 0,
    "urgency_score": 0,
    "overall_score": 0,
    "recommended_action": None,
    "confidence_score": 0.0,
    "raw_ai_json": None,
}


async def analyze_lead(lead) -> dict:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = (
        f"Name: {lead.first_name} {lead.last_name}\n"
        f"Company: {lead.company or 'Unknown'}\n"
        f"Job Title: {lead.job_title or 'Unknown'}\n"
        f"Website: {lead.company_website or 'Unknown'}\n"
        f"Source: {lead.source or 'Unknown'}\n"
        f"Notes: {lead.notes or 'None'}"
    )

    raw_text = None
    for attempt in range(2):
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text = response.content[0].text
            break
        except Exception:
            if attempt == 1:
                return {**_FALLBACK}

    try:
        result = json.loads(raw_text)
        result["raw_ai_json"] = raw_text
        return result
    except (json.JSONDecodeError, TypeError):
        return {**_FALLBACK, "raw_ai_json": raw_text}
```

- [ ] **Step 4.4: Run tests to verify they pass**

```bash
pytest tests/test_analysis_service.py -v
```

Expected: 5 tests pass.

- [ ] **Step 4.5: Commit**

```bash
git add app/services/ai_service.py tests/test_analysis_service.py
git commit -m "feat: add analyze_lead AI service with retry and fallback"
```

---

## Task 5: Analysis Router and Registration

**Files:**
- Create: `app/routers/analysis.py`
- Modify: `app/main.py`
- Create: `tests/test_analysis.py`

- [ ] **Step 5.1: Write the failing endpoint tests**

Create `tests/test_analysis.py`:

```python
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db

_NOW = datetime(2026, 6, 16, 12, 0, 0)

_ANALYSIS_DICT = {
    "company_summary": "A tech company",
    "persona_type": "Champion",
    "pain_points": "Manual processes",
    "buying_signals": "Requested demo",
    "objections": "Budget concerns",
    "fit_score": 75,
    "urgency_score": 60,
    "overall_score": 70,
    "recommended_action": "Schedule call",
    "confidence_score": 0.8,
    "raw_ai_json": '{"fit_score": 75}',
}


def _make_lead(**kwargs):
    defaults = dict(
        id=1, first_name="Jane", last_name="Smith",
        email="jane@example.com", company="Acme Corp",
        job_title="VP Sales", company_website="acme.com",
        source="LinkedIn", notes=None, status="new",
        created_at=_NOW, updated_at=_NOW,
    )
    defaults.update(kwargs)
    lead = MagicMock()
    for k, v in defaults.items():
        setattr(lead, k, v)
    return lead


def _scalar_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


@asynccontextmanager
async def _client_with_db(mock_session):
    async def _override():
        yield mock_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_analyze_lead_returns_200_with_correct_structure():
    lead = _make_lead()
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(lead))

    async def _refresh(obj):
        obj.id = 1
        obj.created_at = _NOW

    mock.refresh = AsyncMock(side_effect=_refresh)

    with patch(
        "app.routers.analysis.ai_service.analyze_lead",
        new=AsyncMock(return_value=_ANALYSIS_DICT),
    ):
        async with _client_with_db(mock) as client:
            response = await client.post("/leads/1/analyze")

    assert response.status_code == 200
    data = response.json()
    assert data["lead_id"] == 1
    assert data["fit_score"] == 75
    assert data["urgency_score"] == 60
    assert data["overall_score"] == 70
    assert data["confidence_score"] == 0.8
    assert data["persona_type"] == "Champion"


async def test_analyze_lead_returns_404_for_missing_lead():
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(None))

    with patch(
        "app.routers.analysis.ai_service.analyze_lead",
        new=AsyncMock(return_value=_ANALYSIS_DICT),
    ):
        async with _client_with_db(mock) as client:
            response = await client.post("/leads/999/analyze")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"
```

- [ ] **Step 5.2: Run test to verify it fails**

```bash
pytest tests/test_analysis.py -v
```

Expected: `ImportError` or `404` because the router doesn't exist yet.

- [ ] **Step 5.3: Create the analysis router**

Create `app/routers/analysis.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.lead import Lead
from app.models.analysis import LeadAnalysis
from app.schemas.analysis import LeadAnalysisRead
from app.services import ai_service

router = APIRouter(prefix="/leads", tags=["analysis"])


@router.post("/{lead_id}/analyze", response_model=LeadAnalysisRead, status_code=status.HTTP_200_OK)
async def analyze_lead_endpoint(lead_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    analysis_dict = await ai_service.analyze_lead(lead)
    analysis = LeadAnalysis(**analysis_dict, lead_id=lead_id)
    db.add(analysis)
    lead.status = "analyzed"
    await db.commit()
    await db.refresh(analysis)
    return analysis
```

- [ ] **Step 5.4: Register the router in main.py**

Open `app/main.py` and replace the entire file:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, get_db
from app.routers.leads import router as leads_router
from app.routers.analysis import router as analysis_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="GTM AI System", version="0.1.0", lifespan=lifespan)

app.include_router(leads_router)
app.include_router(analysis_router)


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
```

- [ ] **Step 5.5: Run tests to verify they pass**

```bash
pytest tests/test_analysis.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5.6: Run the full test suite to check for regressions**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5.7: Commit**

```bash
git add app/routers/analysis.py app/main.py tests/test_analysis.py
git commit -m "feat: add POST /leads/{lead_id}/analyze endpoint"
```

---

## Task 6: Alembic Migration

**Files:**
- Modify: `alembic/env.py`
- Generate: `alembic/versions/<hash>_add_lead_analysis_table.py`

**Context:** `alembic/env.py` imports `Base` from `app.database` but never imports the model classes. SQLAlchemy's autogenerate only detects tables whose model classes have been imported into memory before `target_metadata` is evaluated. Without importing the models, autogenerate produces an empty migration.

- [ ] **Step 6.1: Import models in alembic/env.py**

Open `alembic/env.py`. Find the block of imports at the top and add one import line after the existing `app` imports. The full imports section should look like this (only the `import app.models` line is new — everything else is unchanged):

```python
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.database import Base
import app.models  # ensures all model classes register with Base.metadata
```

- [ ] **Step 6.2: Generate the migration**

Run this from the project root (outside Docker, since Alembic is installed locally):

```bash
alembic revision --autogenerate -m "add lead_analysis table"
```

A new file appears in `alembic/versions/` named `<hash>_add_lead_analysis_table.py`.

- [ ] **Step 6.3: Verify the generated migration**

Open the generated file. The `upgrade()` function must create the `lead_analysis` table with all 14 columns and a foreign key to `leads.id`. It should look similar to this (hash values will differ):

```python
def upgrade() -> None:
    op.create_table(
        'lead_analysis',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('company_summary', sa.Text(), nullable=True),
        sa.Column('persona_type', sa.String(length=100), nullable=True),
        sa.Column('pain_points', sa.Text(), nullable=True),
        sa.Column('buying_signals', sa.Text(), nullable=True),
        sa.Column('objections', sa.Text(), nullable=True),
        sa.Column('fit_score', sa.Integer(), nullable=True),
        sa.Column('urgency_score', sa.Integer(), nullable=True),
        sa.Column('overall_score', sa.Integer(), nullable=True),
        sa.Column('recommended_action', sa.String(length=100), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('raw_ai_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('lead_analysis')
```

If the file is empty or missing the `lead_analysis` table, the model import in Step 6.1 didn't take effect — double-check the `alembic/env.py` edit and re-run.

- [ ] **Step 6.4: Commit**

```bash
git add alembic/env.py alembic/versions/
git commit -m "chore: add Alembic migration for lead_analysis table"
```

---

## Task 7: Final Verification and PR

- [ ] **Step 7.1: Run the complete test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass. Count should include the new tests from tasks 2–5.

- [ ] **Step 7.2: Push the branch**

```bash
git push -u origin feature/lead-analysis
```

- [ ] **Step 7.3: Open a pull request**

```bash
gh pr create \
  --title "feat: Phase 3 — Claude AI lead analysis endpoint" \
  --body "$(cat <<'EOF'
## Summary

- Adds `POST /leads/{lead_id}/analyze` endpoint
- Calls Claude Haiku (`claude-haiku-4-5-20251001`) via Anthropic SDK to score and narrate leads
- Stores result in new `lead_analysis` table with FK to `leads`
- Updates lead status to `"analyzed"` after successful analysis
- Includes retry (once) and safe fallback for API failures or malformed JSON

## Test plan

- [ ] `pytest tests/test_analysis_model.py` — model columns and FK constraint
- [ ] `pytest tests/test_analysis_schemas.py` — schema validation
- [ ] `pytest tests/test_analysis_service.py` — AI service: happy path, malformed JSON, retry logic, score types
- [ ] `pytest tests/test_analysis.py` — endpoint: 200 with correct structure, 404 for missing lead
- [ ] `pytest tests/` — full suite passes with no regressions
EOF
)"
```

---

## Self-Review Notes

**Spec coverage check:**
- [x] `lead_analysis` DB model with all 14 columns — Task 2
- [x] `LeadAnalysisCreate` and `LeadAnalysisRead` schemas — Task 3
- [x] `analyze_lead()` using Anthropic SDK, claude-haiku-4-5-20251001 — Task 4
- [x] System prompt: cautious language, JSON only, conservative defaults — Task 4
- [x] Retry once on exception — Task 4
- [x] Malformed JSON → safe fallback — Task 4
- [x] `POST /leads/{lead_id}/analyze` → 404 if missing — Task 5
- [x] Store result, update lead.status = "analyzed" — Task 5
- [x] Return `LeadAnalysisRead` — Task 5
- [x] Register router in main.py — Task 5
- [x] Alembic migration — Task 6
- [x] `anthropic>=0.25.0` in requirements.txt — Task 1
- [x] `ANTHROPIC_API_KEY` in config and .env.example — Task 1
- [x] Tests: 200 correct structure, 404, malformed JSON fallback, score types — Tasks 4 & 5
- [x] Mocked Anthropic in all tests — Tasks 4 & 5
