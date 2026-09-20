"""Seasonal crop planner (Gemini-reasoned rotation advice).

Given the farm's soil, climate outlook and current crop, recommends the next
seasons' rotation with regenerative practices — grounded in the advisory
corpus, structured JSON, in the farmer's language. Follows the same provider-
injection pattern as the advisory pipeline.
"""

import json

from ..models.schemas import DataProvenance, PlannerRequest, PlannerResponse
from ..storage import Store
from .farms import infer_district
from .gemini import GeminiService
from .rag import Retriever
from .satellite import SatelliteProvider
from .soil import SoilClient
from .weather import WeatherClient

_LANGUAGE_NAMES = {"en": "English", "te": "Telugu", "hi": "Hindi"}

PLANNER_PROMPT = """You are AgriNet's seasonal crop planner for Indian smallholder farmers.
Recommend a crop rotation for the next 2-3 seasons (kharif / rabi / summer) after the farmer's current crop.
STRICT RULES:
- Recommend ONLY from the field data and advisory excerpts provided. Favour regenerative choices: legume rotations, green manure, residue retention, reduced tillage.
- Consider the soil pH, organic carbon and texture, and the climate outlook, and say WHY each crop fits.
- Never invent input dosages (fertiliser/pesticide); direct specifics to the local Krishi Vigyan Kendra (KVK).
- Cite advisory excerpts you rely on.
- Simple language (8th-grade level).
- Respond with JSON only, matching exactly:
{
  "rotation": [{"season": str, "crop": str, "why": str}],
  "regenerative_plan": [str],
  "soil_note": str,
  "citations": [{"source": str, "excerpt_ref": str}],
  "confidence_note": str
}"""


class PlannerService:
    def __init__(self, satellite: SatelliteProvider, soil: SoilClient,
                 weather: WeatherClient, retriever: Retriever,
                 gemini: GeminiService, store: Store):
        self.satellite = satellite
        self.soil = soil
        self.weather = weather
        self.retriever = retriever
        self.gemini = gemini
        self.store = store

    def plan(self, req: PlannerRequest) -> PlannerResponse:
        sat = self.satellite.get_features(req.lat, req.lon)
        soil = self.soil.get_properties(req.lat, req.lon)
        weather = self.weather.get_forecast(req.lat, req.lon)

        chunks = self.retriever.retrieve(
            f"{req.current_crop} rotation legume green manure regenerative "
            f"soil organic carbon intercropping", k=4,
        )
        prompt = self._build_prompt(req, sat, soil, weather, chunks)
        result = self.gemini.generate_json("planner", prompt, language=req.language)

        self.store.log_query("planner", req.lat, req.lon, req.current_crop,
                             infer_district(req.lat, req.lon), req.language)

        return PlannerResponse(
            **result,
            provenance=DataProvenance(satellite=sat, soil=soil, weather=weather),
            language=req.language,
        )

    def _build_prompt(self, req: PlannerRequest, sat: dict, soil: dict,
                      weather: dict, chunks) -> str:
        excerpts = "\n\n".join(
            f"[{c.id}] (source: {c.source})\n{c.text}" for c in chunks
        ) or "(no advisory excerpts matched)"
        language_line = (
            f"Write every farmer-facing string in {_LANGUAGE_NAMES[req.language]}."
            if req.language != "en" else ""
        )
        return f"""{PLANNER_PROMPT}

FIELD DATA (location {req.lat:.2f}, {req.lon:.2f} — current crop: {req.current_crop}):
- Satellite (source: {sat.get('source')}): {json.dumps({k: v for k, v in sat.items() if k != 'source'})}
- Soil 0-5cm (source: {soil.get('source')}): {json.dumps({k: v for k, v in soil.items() if k != 'source'})}
- Climate outlook (source: {weather.get('source')}): {json.dumps({k: v for k, v in weather.items() if k not in ('source', 'daily')})}

RETRIEVED ADVISORY EXCERPTS:
{excerpts}

{language_line}
Produce the rotation plan JSON now."""
