from fastapi import APIRouter, Depends, Query

from ..deps import get_warnings_service
from ..models.schemas import WarningItem
from ..services.warnings import WarningsService

router = APIRouter(prefix="/api", tags=["warnings"])


@router.get("/warnings", response_model=list[WarningItem])
def warnings(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180),
             service: WarningsService = Depends(get_warnings_service)):
    return service.for_location(lat, lon)
