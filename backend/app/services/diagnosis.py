"""Disease-diagnosis pipeline (spec §5.2).

leaf image → RAG grounding (via crop hint) → Gemini multimodal → structured
diagnosis → anonymized DiseaseReport → outbreak check → federation alert.
"""

import logging

from ..models.schemas import DiagnosisResponse
from ..storage import Store
from .federation import FederationService
from .gemini import GeminiService
from .rag import Retriever

log = logging.getLogger(__name__)

_LANGUAGE_NAMES = {"en": "English", "te": "Telugu", "hi": "Hindi"}

DIAGNOSIS_PROMPT = """You are AgriNet's crop disease diagnostic assistant for Indian farmers.
Examine the attached leaf/plant photo.
STRICT RULES:
- If the image is unclear or your confidence is low, say so and set escalate_to_expert=true recommending the local Krishi Vigyan Kendra (KVK). Never guess.
- NEVER state chemical/pesticide dosages. Treatment steps may name cultural and organic practices; chemical interventions must say "confirm product and dosage with your KVK".
- Ground treatment steps in the advisory excerpts provided; cite them.
- Simple language, 8th-grade level.
- Respond with JSON only, matching exactly:
{
  "disease": str,
  "confidence": "high"|"medium"|"low",
  "symptoms_observed": [str],
  "treatment_steps": [str],
  "organic_options": [str],
  "escalate_to_expert": bool,
  "citations": [{"source": str, "excerpt_ref": str}],
  "safety_note": str
}"""


class DiagnosisService:
    def __init__(self, retriever: Retriever, gemini: GeminiService,
                 federation: FederationService, store: Store):
        self.retriever = retriever
        self.gemini = gemini
        self.federation = federation
        self.store = store

    def diagnose(self, image_bytes: bytes, image_mime: str,
                 crop: str | None, language: str, district: str,
                 lat: float | None = None, lon: float | None = None) -> DiagnosisResponse:
        chunks = self.retriever.retrieve(
            f"{crop or 'crop'} disease pest symptoms treatment", k=4
        )
        prompt = self._build_prompt(crop, language, chunks)
        result = self.gemini.generate_json(
            "diagnosis", prompt, language=language,
            image_bytes=image_bytes, image_mime=image_mime,
        )

        self.store.log_query("diagnose", lat, lon, crop, district, language)

        alert = None
        confidence = result.get("confidence", "low")
        if confidence in ("high", "medium") and result.get("disease"):
            alert = self.federation.record_report_and_check_outbreak(
                disease=result["disease"], crop=crop,
                district=district, confidence=confidence,
            )

        return DiagnosisResponse(
            **result,
            alert_triggered=alert is not None,
            language=language,
        )

    @staticmethod
    def _build_prompt(crop: str | None, language: str, chunks) -> str:
        excerpts = "\n\n".join(
            f"[{c.id}] (source: {c.source})\n{c.text}" for c in chunks
        ) or "(no advisory excerpts matched)"
        crop_line = (
            f"The farmer says the crop is: {crop}."
            if crop else "The crop is not specified — identify it from the image first."
        )
        language_line = (
            f"Write every farmer-facing string in {_LANGUAGE_NAMES.get(language, 'English')}."
            if language != "en" else ""
        )
        return f"""{DIAGNOSIS_PROMPT}

{crop_line}

ADVISORY EXCERPTS FOR GROUNDING TREATMENTS:
{excerpts}

{language_line}
Produce the diagnosis JSON now."""
