from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_ask_service
from ..models.schemas import AskRequest, AskResponse
from ..services.ask import AskService
from ..services.gemini import GeminiError

router = APIRouter(prefix="/api", tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, service: AskService = Depends(get_ask_service)):
    try:
        return service.ask(req)
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
