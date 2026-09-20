"""AgriNet Protocol v1 endpoints — every state node exposes these.
The schema is defined in models/protocol.py; docs/AGRINET_PROTOCOL.md is the
human-readable spec."""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException

from ..deps import Container, get_container, get_federation_service
from ..models.protocol import (
    Alert, Health, Insight, ModelRegistryEntry, Peer, PROTOCOL_VERSION,
)
from ..services.federation import FederationService

router = APIRouter(prefix="/v1", tags=["federation"])


def verify_federation_token(
    c: Container = Depends(get_container),
    x_agrinet_token: str | None = Header(default=None),
):
    """Shared-secret gate on federation WRITE endpoints. When
    FEDERATION_TOKEN is unset (local dev) the endpoints stay open; when set,
    peers must send it as X-AgriNet-Token. Reads stay public — the protocol
    is an open data good."""
    expected = c.settings.federation_token
    if not expected:
        return
    if not x_agrinet_token or not secrets.compare_digest(x_agrinet_token, expected):
        raise HTTPException(status_code=401, detail="invalid federation token")


@router.get("/health", response_model=Health)
def health(c: Container = Depends(get_container)):
    return Health(state_id=c.settings.state_id, state_name=c.settings.state_name)


@router.get("/alerts")
def list_alerts(service: FederationService = Depends(get_federation_service)):
    return {"protocol_version": PROTOCOL_VERSION, "alerts": service.list_alerts()}


@router.post("/alerts", status_code=202,
             dependencies=[Depends(verify_federation_token)])
def receive_alert(alert: Alert,
                  service: FederationService = Depends(get_federation_service)):
    created = service.receive_alert(alert)
    return {"accepted": True, "duplicate": not created, "id": alert.id}


@router.get("/insights")
def list_insights(service: FederationService = Depends(get_federation_service)):
    return {"protocol_version": PROTOCOL_VERSION, "insights": service.list_insights()}


@router.post("/insights", status_code=202,
             dependencies=[Depends(verify_federation_token)])
def receive_insight(insight: Insight,
                    service: FederationService = Depends(get_federation_service)):
    created = service.add_insight(insight)
    return {"accepted": True, "duplicate": not created, "id": insight.id}


@router.get("/peers", response_model=list[Peer])
def peers(service: FederationService = Depends(get_federation_service)):
    return service.peers()


@router.get("/models", response_model=list[ModelRegistryEntry])
def models(service: FederationService = Depends(get_federation_service)):
    return service.model_registry()
