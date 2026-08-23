from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_advisory_service
from ..models.schemas import AdvisoryRequest, AdvisoryResponse
from ..services.advisory import AdvisoryService
from ..services.gemini import GeminiError

router = APIRouter(prefix="/api", tags=["advisory"])


@router.post("/advisory", response_model=AdvisoryResponse)
def get_advisory(req: AdvisoryRequest,
                 service: AdvisoryService = Depends(get_advisory_service)):
    try:
        return service.get_advisory(req)
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
