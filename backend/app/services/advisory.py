"""Advisory pipeline orchestrator (spec §5.1).

location → satellite + soil + weather features → RAG grounding → one Gemini
call with structured-JSON output → provenance-stamped response. Providers are
injected, so each stage is independently testable and swappable.
"""

import json
import logging

from ..models.schemas import AdvisoryRequest, AdvisoryResponse, DataProvenance
from ..storage import Store
from .gemini import GeminiService
from .geocode import Geocoder
from .rag import Retriever
from .satellite import SatelliteProvider
from .soil import SoilClient
from .weather import WeatherClient

log = logging.getLogger(__name__)

_LANGUAGE_NAMES = {"en": "English", "te": "Telugu", "hi": "Hindi"}

OFFLINE_NOTE = ("[Offline guidance] Live AI was temporarily unavailable; this is "
                "pre-verified general guidance, not location-specific reasoning.")

SYSTEM_PROMPT = """You are AgriNet, an agricultural advisory assistant for Indian farmers.
STRICT RULES:
- Advise ONLY from the field data and the advisory excerpts provided below. If the data is insufficient for a recommendation, say so plainly.
- NEVER invent pesticide or fungicide dosages. For any chemical intervention, direct the farmer to their local Krishi Vigyan Kendra (KVK).
- Attach a citation (source + excerpt_ref) for every recommendation that draws on an advisory excerpt.
- Write farmer-facing text in simple language (8th-grade reading level). Short sentences.
- Respond with JSON only, matching exactly this schema:
{
  "advisory": [{"title": str, "detail": str, "urgency": "high"|"medium"|"low"}],
  "regenerative_recommendations": [str],
  "irrigation_guidance": str,
  "risk_flags": [{"type": "pest"|"weather"|"soil", "message": str}],
  "citations": [{"source": str, "excerpt_ref": str}],
  "confidence_note": str
}"""


class AdvisoryService:
    def __init__(self, satellite: SatelliteProvider, soil: SoilClient,
                 weather: WeatherClient, retriever: Retriever,
                 gemini: GeminiService, store: Store, geocoder: Geocoder):
        self.satellite = satellite
        self.soil = soil
        self.weather = weather
        self.retriever = retriever
        self.gemini = gemini
        self.store = store
        self.geocoder = geocoder

    def get_advisory(self, req: AdvisoryRequest) -> AdvisoryResponse:
        sat = self.satellite.get_features(req.lat, req.lon)
        soil = self.soil.get_properties(req.lat, req.lon)
        weather = self.weather.get_forecast(req.lat, req.lon)

        stress = self._detect_stress(sat, weather)
        chunks = self.retriever.retrieve(f"{req.crop} {stress} kharif season", k=4)

        prompt = self._build_prompt(req, sat, soil, weather, chunks)
        result = self.gemini.generate_json("advisory", prompt, language=req.language)
        fallback = result.pop("_fallback", False)
        if fallback:
            note = result.get("confidence_note") or ""
            result["confidence_note"] = (OFFLINE_NOTE + (" " + note if note else ""))

        district = req.district or self.geocoder.district_for(req.lat, req.lon)
        self.store.log_query("advisory", req.lat, req.lon, req.crop,
                             district, req.language)

        return AdvisoryResponse(
            **result,
            district=district,
            offline_guidance=fallback,
            provenance=DataProvenance(satellite=sat, soil=soil, weather=weather),
            language=req.language,
        )

    @staticmethod
    def _detect_stress(sat: dict, weather: dict) -> str:
        parts = []
        if sat.get("ndvi_trend") == "declining":
            parts.append("declining crop vigour water stress")
        rain = weather.get("rain_next_7d_mm")
        if rain is not None and rain < 20:
            parts.append("low rainfall drought")
        elif rain is not None and rain > 80:
            parts.append("heavy rain waterlogging")
        hum = weather.get("mean_humidity_pct")
        if hum is not None and hum > 75:
            parts.append("high humidity pest disease planthopper")
        return " ".join(parts) or "general management"

    def _build_prompt(self, req: AdvisoryRequest, sat: dict, soil: dict,
                      weather: dict, chunks) -> str:
        excerpts = "\n\n".join(
            f"[{c.id}] (source: {c.source})\n{c.text}" for c in chunks
        ) or "(no advisory excerpts matched)"
        language_line = (
            f"Write every farmer-facing string in {_LANGUAGE_NAMES[req.language]}."
            if req.language != "en" else ""
        )
        return f"""{SYSTEM_PROMPT}

FIELD DATA (location {req.lat:.2f}, {req.lon:.2f} — crop: {req.crop}):
- Satellite (source: {sat.get('source')}): {json.dumps({k: v for k, v in sat.items() if k != 'source'})}
- Soil 0-5cm (source: {soil.get('source')}): {json.dumps({k: v for k, v in soil.items() if k != 'source'})}
- Weather 7-day forecast (source: {weather.get('source')}): {json.dumps({k: v for k, v in weather.items() if k not in ('source', 'daily')})}

RETRIEVED ADVISORY EXCERPTS:
{excerpts}

{language_line}
Produce the advisory JSON now."""
