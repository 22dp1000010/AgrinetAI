"""Node configuration. All secrets and per-node identity come from the
environment (.env in the repo root), never from code."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
REPO_ROOT = BACKEND_DIR.parent

STATE_NAMES = {
    "TS": "Telangana",
    "OD": "Odisha",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    # Vertex AI mode: authenticate with the runtime service account (ADC)
    # instead of an API key — no key to expire, billed to the GCP project,
    # pay-as-you-go rate limits. Local dev keeps the API-key / DEMO_MODE paths.
    use_vertex_ai: bool = False
    vertex_project: str = ""
    vertex_location: str = "global"
    state_id: str = "TS"
    port: int = 8001
    peers: str = ""
    demo_mode: bool = True
    # If a live Gemini call fails (quota, invalid key, network), serve the
    # canned demo response instead of erroring — the demo never dies.
    demo_fallback: bool = True
    ee_enabled: bool = False
    ee_project: str = ""
    outbreak_threshold: int = 3
    outbreak_window_days: int = 7
    # Storage backend: "sqlite" (local default — file per node) or
    # "firestore" (Cloud Run — persistent, shared project database).
    db_backend: str = "sqlite"
    firestore_project: str = ""
    # Overridable so tests can point at a throwaway database.
    db_path: str = ""
    # Shared secret required on federation write endpoints (POST /v1/*).
    # Empty = open (local dev). Peers send it as X-AgriNet-Token.
    federation_token: str = ""
    # Comma-separated allowed CORS origins; "*" for local dev.
    cors_origins: str = "*"

    @field_validator("gemini_api_key", "federation_token", mode="after")
    @classmethod
    def _strip_secret_whitespace(cls, v: str) -> str:
        # Secret managers and shell pipes commonly append trailing newlines;
        # a stray \n breaks header values and token comparison.
        return v.strip()

    @property
    def state_name(self) -> str:
        return STATE_NAMES.get(self.state_id, self.state_id)

    @property
    def peer_urls(self) -> list[str]:
        return [u.strip().rstrip("/") for u in self.peers.split(",") if u.strip()]

    @property
    def database_path(self) -> Path:
        if self.db_path:
            return Path(self.db_path)
        return DATA_DIR / f"agrinet_{self.state_id.lower()}.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
