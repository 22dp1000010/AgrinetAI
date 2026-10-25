"""Composition root: builds the service graph once per app and exposes
FastAPI dependency functions. Routers depend on these accessors only — they
never construct services themselves — so tests can swap any piece."""

from fastapi import Request

from .config import Settings, get_settings
from .storage import build_store
from .services.advisory import AdvisoryService
from .services.ask import AskService
from .services.diagnosis import DiagnosisService
from .services.federation import FederationService
from .services.gemini import GeminiService
from .services.geocode import Geocoder
from .services.planner import PlannerService
from .services.rag import Retriever
from .services.satellite import build_provider
from .services.soil import SoilClient
from .services.warnings import WarningsService
from .services.weather import WeatherClient


class Container:
    """Holds one instance of each service for the app's lifetime."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.store = build_store(self.settings)
        # Direct SQLite handle for tests/tooling; None on Firestore.
        self.conn = getattr(self.store, "conn", None)
        self.retriever = Retriever()
        self.geocoder = Geocoder()
        self.gemini = GeminiService(self.settings, self.store)
        self.satellite = build_provider(self.settings.ee_enabled, self.settings.ee_project)
        self.soil = SoilClient()
        self.weather = WeatherClient()
        self.federation = FederationService(self.settings, self.store)
        self.advisory = AdvisoryService(
            self.satellite, self.soil, self.weather,
            self.retriever, self.gemini, self.store, self.geocoder,
        )
        self.diagnosis = DiagnosisService(
            self.retriever, self.gemini, self.federation, self.store,
        )
        self.ask = AskService(self.retriever, self.gemini, self.store, self.geocoder)
        self.warnings = WarningsService(self.retriever, self.store, self.geocoder)
        self.planner = PlannerService(
            self.satellite, self.soil, self.weather,
            self.retriever, self.gemini, self.store, self.geocoder,
        )


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


def get_warnings_service(request: Request) -> WarningsService:
    return get_container(request).warnings


def get_planner_service(request: Request) -> PlannerService:
    return get_container(request).planner
