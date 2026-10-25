from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..deps import Container, get_container, get_diagnosis_service
from ..models.schemas import DiagnosisResponse
from ..services.diagnosis import DiagnosisService
from ..services.gemini import GeminiError

router = APIRouter(prefix="/api", tags=["diagnose"])

_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 8 * 1024 * 1024


@router.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose(
    image: UploadFile = File(...),
    crop: str | None = Form(None),
    language: str = Form("en"),
    district: str | None = Form(None),
    lat: float | None = Form(None),
    lon: float | None = Form(None),
    service: DiagnosisService = Depends(get_diagnosis_service),
    c: Container = Depends(get_container),
):
    mime = image.content_type or "image/jpeg"
    if mime not in _ALLOWED_MIME:
        raise HTTPException(415, f"Unsupported image type: {mime}")
    data = await image.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(413, "Image too large (max 8 MB)")
    if language not in ("en", "te", "hi"):
        raise HTTPException(422, "language must be en, te or hi")

    resolved_district = district or (
        c.geocoder.district_for(lat, lon)
        if lat is not None and lon is not None else "Unknown"
    )
    try:
        return service.diagnose(
            image_bytes=data, image_mime=mime, crop=crop,
            language=language, district=resolved_district, lat=lat, lon=lon,
        )
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
