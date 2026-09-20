from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_planner_service
from ..models.schemas import PlannerRequest, PlannerResponse
from ..services.gemini import GeminiError
from ..services.planner import PlannerService

router = APIRouter(prefix="/api", tags=["planner"])


@router.post("/planner", response_model=PlannerResponse)
def plan_season(req: PlannerRequest,
                service: PlannerService = Depends(get_planner_service)):
    try:
        return service.plan(req)
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
