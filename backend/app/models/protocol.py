"""AgriNet Protocol v1 — the shared open schema for state-to-state exchange.

These models ARE the interoperability contract: any state node that speaks
this schema can join the federation. Documented for humans in
docs/AGRINET_PROTOCOL.md; the OpenAPI spec is generated from these models.
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

PROTOCOL_VERSION = "1.0"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Alert(BaseModel):
    """Cross-state early warning (e.g. a disease outbreak)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    origin_state: str = Field(min_length=2, max_length=8, description="State code, e.g. TS")
    disease: str = Field(min_length=1)
    crop: str | None = None
    district: str | None = None
    severity: Literal["low", "medium", "high"] = "medium"
    report_count: int = Field(ge=1)
    window_days: int = Field(ge=1)
    message: str | None = None
    created_at: datetime = Field(default_factory=_now)


class Insight(BaseModel):
    """Shareable agronomic finding (practice outcome, yield signal, etc.)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    state_id: str = Field(min_length=2, max_length=8)
    district: str | None = None
    crop: str | None = None
    type: Literal["practice", "yield", "pest", "weather", "market"] = "practice"
    summary: str = Field(min_length=1)
    evidence: dict | None = None
    created_at: datetime = Field(default_factory=_now)


class Peer(BaseModel):
    """A federation member node."""

    state_id: str
    name: str
    base_url: str
    last_sync: datetime | None = None


class ModelRegistryEntry(BaseModel):
    """Registry stub proving the schema supports sharing fine-tuned models
    (e.g. state-specific Gemma disease classifiers) across the federation."""

    name: str
    version: str
    task: str
    trained_by: str
    artifact_url: str | None = None
    published_at: datetime = Field(default_factory=_now)


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    state_id: str
    state_name: str
    protocol_version: str = PROTOCOL_VERSION
