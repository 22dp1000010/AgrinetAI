"""Composition root: builds the service graph once per app and exposes
FastAPI dependency functions. Routers depend on these accessors only — they
never construct services themselves — so tests can swap any piece."""

from fastapi import Request

from . import db
from .config import Settings, get_settings
from .services.advisory import AdvisoryService
from .services.ask import AskService
from .services.diagnosis import DiagnosisService
from .services.federation import FederationService
from .services.gemini import GeminiService
from .services.rag import Retriever
from .services.satellite import build_provider
from .services.soil import SoilClient
from .services.weather import WeatherClient


class Container:
    """Holds one instance of each service for the app's lifetime."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.conn = db.connect(self.settings.database_path)
        self.retriever = Retriever()
        self.gemini = GeminiService(self.settings, self.conn)
        self.satellite = build_provider(self.settings.ee_enabled, self.settings.ee_project)
        self.soil = SoilClient()
        self.weather = WeatherClient()
        self.federation = FederationService(self.settings, self.conn)
        self.advisory = AdvisoryService(
            self.satellite, self.soil, self.weather,
            self.retriever, self.gemini, self.conn,
        )
        self.diagnosis = DiagnosisService(
            self.retriever, self.gemini, self.federation, self.conn,
        )
        self.ask = AskService(self.retriever, self.gemini, self.conn)


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_advisory_service(request: Request) -> AdvisoryService:
    return get_container(request).advisory


def get_diagnosis_service(request: Request) -> DiagnosisService:
    return get_container(request).diagnosis


def get_ask_service(request: Request) -> AskService:
    return get_container(request).ask


def get_federation_service(request: Request) -> FederationService:
    return get_container(request).federation
