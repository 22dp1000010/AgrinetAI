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
    district: str | None = None
    offline_guidance: bool = False
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
    offline_guidance: bool = False
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
    offline_guidance: bool = False
    language: Language = "en"


# --- farmer outbreak warnings ---

class Prevention(BaseModel):
    text: str
    source: str


class WarningItem(BaseModel):
    """An active outbreak alert made farmer-facing: scoped to their district
    or flagged as a regional/federated early warning, with a grounded
    prevention tip retrieved from the advisory corpus."""
    disease: str
    crop: str | None = None
    district: str | None = None
    severity: str
    origin_state: str
    from_peer: bool
    scope: Literal["your_district", "regional"]
    message: str | None = None
    created_at: str
    prevention: Prevention | None = None


# --- seasonal crop planner ---

class PlannerRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    current_crop: str = Field(min_length=1)
    language: Language = "en"


class RotationStep(BaseModel):
    season: str
    crop: str
    why: str


class PlannerResponse(BaseModel):
    rotation: list[RotationStep]
    regenerative_plan: list[str] = []
    soil_note: str | None = None
    citations: list[Citation] = []
    confidence_note: str | None = None
    provenance: DataProvenance
    offline_guidance: bool = False
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
