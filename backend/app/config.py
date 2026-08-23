"""Node configuration. All secrets and per-node identity come from the
environment (.env in the repo root), never from code."""

from functools import lru_cache
from pathlib import Path

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
    # Overridable so tests can point at a throwaway database.
    db_path: str = ""

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
