"""Free-form Q&A pipeline (spec §5.3) — voice transcripts arrive here as text
(the browser does STT/TTS via the Web Speech API)."""

from ..models.schemas import AskRequest, AskResponse, Citation
from ..storage import Store
from .gemini import GeminiService
from .geocode import Geocoder
from .rag import Retriever

_LANGUAGE_NAMES = {"en": "English", "te": "Telugu", "hi": "Hindi"}

ASK_PROMPT = """You are AgriNet, an agricultural Q&A assistant for Indian farmers.
STRICT RULES:
- Answer ONLY from the advisory excerpts provided. If they don't cover the question, say you don't have verified guidance and recommend the local Krishi Vigyan Kendra (KVK).
- NEVER invent pesticide or fungicide dosages.
- Simple language, 8th-grade level, short sentences (the answer may be read aloud).
- Respond with JSON only: {"answer": str, "citations": [{"source": str, "excerpt_ref": str}]}"""


class AskService:
    def __init__(self, retriever: Retriever, gemini: GeminiService,
                 store: Store, geocoder: Geocoder):
        self.retriever = retriever
        self.gemini = gemini
        self.store = store
        self.geocoder = geocoder

    def ask(self, req: AskRequest) -> AskResponse:
        chunks = self.retriever.retrieve(
            f"{req.crop or ''} {req.question}", k=4
        )
        excerpts = "\n\n".join(
            f"[{c.id}] (source: {c.source})\n{c.text}" for c in chunks
        ) or "(no advisory excerpts matched)"
        language_line = (
            f"Answer in {_LANGUAGE_NAMES[req.language]}."
            if req.language != "en" else ""
        )
        prompt = f"""{ASK_PROMPT}

FARMER'S QUESTION: {req.question}

ADVISORY EXCERPTS:
{excerpts}

{language_line}
Produce the answer JSON now."""
        result = self.gemini.generate_json("ask", prompt, language=req.language)
        fallback = result.pop("_fallback", False)
        if fallback:
            # Live AI unavailable: answer extractively from the retrieved
            # corpus so the reply still matches THIS question and stays
            # grounded — never the same canned text for every query.
            result = self._extractive_answer(chunks, result)

        district = req.district or (
            self.geocoder.district_for(req.lat, req.lon)
            if req.lat is not None and req.lon is not None else None
        )
        self.store.log_query("ask", req.lat, req.lon, req.crop,
                             district, req.language)
        return AskResponse(**result, offline_guidance=fallback,
                           language=req.language)

    @staticmethod
    def _extractive_answer(chunks, canned: dict) -> dict:
        if not chunks:
            return canned  # last resort: the canned fixture
        top = chunks[0]
        answer = (
            f"Live AI is temporarily unavailable, so here is the verified "
            f"advisory text that best matches your question — from {top.source}: "
            f"{top.text}"
        )
        return {
            "answer": answer,
            "citations": [Citation(source=c.source, excerpt_ref=c.id).model_dump()
                          for c in chunks[:2]],
        }
