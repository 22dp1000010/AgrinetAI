"""FastAPI app factory. One codebase runs as any state node — identity comes
from STATE_ID/PORT/PEERS in the environment (spec §3)."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .deps import Container
from .routers import advisory, ask, dashboard, diagnose, federation

logging.basicConfig(level=logging.INFO)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title=f"AgriNet Node — {settings.state_name}",
        description="Federated agricultural intelligence node (AgriNet Protocol v1)",
        version="0.1.0",
    )
    app.state.container = Container(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # hackathon prototype; restrict per-state in production
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(advisory.router)
    app.include_router(diagnose.router)
    app.include_router(ask.router)
    app.include_router(dashboard.router)
    app.include_router(federation.router)

    @app.get("/")
    def root():
        return {
            "service": "AgriNet state node",
            "state": settings.state_name,
            "docs": "/docs",
            "protocol": "/v1/health",
        }

    return app


app = create_app()
