"""API DTOs for the farmer/officer-facing endpoints (not the federation
protocol — that lives in protocol.py)."""

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["en", "te", "hi"]


# --- advisory ---

class AdvisoryRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    crop: str = Field(min_length=1)
    language: Language = "en"
    farm_id: str | None = None
    district: str | None = None


class AdvisoryItem(BaseModel):
    title: str
    detail: str
    urgency: Literal["high", "medium", "low"] = "medium"


class RiskFlag(BaseModel):
    type: Literal["pest", "weather", "soil"]
    message: str


class Citation(BaseModel):
    source: str
    excerpt_ref: str | None = None
    excerpt: str | None = None


class DataProvenance(BaseModel):
    """What the judges/farmer see in the provenance strip."""
    satellite: dict
    soil: dict
    weather: dict


class AdvisoryResponse(BaseModel):
    advisory: list[AdvisoryItem]
    regenerative_recommendations: list[str] = []
    irrigation_guidance: str | None = None
    risk_flags: list[RiskFlag] = []
    citations: list[Citation] = []
    confidence_note: str | None = None
    provenance: DataProvenance
    language: Language = "en"
    cached: bool = False


# --- diagnosis ---

class DiagnosisResponse(BaseModel):
    disease: str
    confidence: Literal["high", "medium", "low"]
    symptoms_observed: list[str] = []
    treatment_steps: list[str] = []
    organic_options: list[str] = []
    escalate_to_expert: bool = False
    citations: list[Citation] = []
    safety_note: str | None = None
    alert_triggered: bool = False
    language: Language = "en"


# --- ask ---

class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    language: Language = "en"
    lat: float | None = None
    lon: float | None = None
    crop: str | None = None
    district: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    language: Language = "en"


# --- dashboard ---

class DashboardStats(BaseModel):
    state_id: str
    state_name: str
    total_queries: int
    queries_today: int
    top_crops: list[dict]
    top_diseases: list[dict]


class HeatmapPoint(BaseModel):
    lat: float
    lon: float
    count: int
