"""
FastAPI Server Implementation for QUANTUM TRADER V1
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.backend.api.auth import auth_router, validate_auth_settings, verify_token
from src.backend.api.router import api_router, ws_router
from src.backend.services import initialize_services, shutdown_services
from src.backend.utils.config import Config
from src.backend.utils.logger import setup_logging


# The built frontend is served by this API (same-origin). These two exact
# origins are needed only when running the Vite development server locally.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE"]
CORS_ALLOWED_HEADERS = ["Authorization", "Content-Type", "Accept"]


def create_app(config: Config = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    if config is None:
        config = Config()

    # Refuse to expose the application unless a real local administrator and
    # a non-placeholder signing key have been provisioned.
    validate_auth_settings(config.settings)

    database_url = config.settings.database_url
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialize and shut down the service container exactly once."""
        setup_logging(config.settings.log_level)
        print(f"Starting {config.settings.app_name} v{config.settings.version}")
        print(f"Configuration loaded from: {config.settings.project_root}")

        try:
            app.state.services = await initialize_services(config, SessionFactory)
            yield
        finally:
            await shutdown_services()
            engine.dispose()
            print("Shutting down...")

    app = FastAPI(
        title=config.settings.app_name,
        version=config.settings.version,
        description="Professional Quantitative Futures Trading & Intelligence Platform",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.state.config = config
    app.state.engine = engine
    app.state.session_factory = SessionFactory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
    )

    # Login is public; /me performs its own strict bearer-token validation.
    app.include_router(auth_router)
    app.include_router(api_router, dependencies=[Depends(verify_token)])
    app.include_router(ws_router)

    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "version": config.settings.version,
            "mode": "paper",
        }

    frontend_dist = config.settings.project_root / "src" / "frontend" / "dist"

    async def api_info():
        return {
            "name": config.settings.app_name,
            "version": config.settings.version,
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "dashboard": (
                "built"
                if frontend_dist.exists()
                else "not built - run: cd src/frontend && npm install && npm run build"
            ),
        }

    app.add_api_route("/api-info", api_info, methods=["GET"])
    if not frontend_dist.exists():
        app.add_api_route("/", api_info, methods=["GET"])

    if frontend_dist.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dist)), name="static")

        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            """Serve frontend for all non-API routes."""
            if full_path.startswith(("api/", "ws/")):
                raise HTTPException(status_code=404)

            file_path = frontend_dist / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)

            index_path = frontend_dist / "index.html"
            if index_path.exists():
                return FileResponse(index_path)

            return {"message": "Frontend not built yet", "api": "/api/v1"}

    return app
