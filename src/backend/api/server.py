"""
FastAPI Server Implementation for QUANTUM TRADER V1
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.backend.api.router import api_router, ws_router
from src.backend.services import initialize_services, shutdown_services
from src.backend.utils.config import Config
from src.backend.utils.logger import setup_logging


# Security
security = HTTPBearer(auto_error=False)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token (mock for now)."""
    if credentials is None:
        # Allow unauthenticated for development
        return {"user_id": "dev", "username": "developer", "role": "admin"}

    # In production, verify JWT token
    # For now, accept any token for development
    return {"user_id": "dev", "username": "developer", "role": "admin"}


def create_app(config: Config = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    if config is None:
        config = Config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialize and shut down the service container exactly once."""
        setup_logging(config.settings.log_level)
        print(f"Starting {config.settings.app_name} v{config.settings.version}")
        print(f"Configuration loaded from: {config.settings.project_root}")

        try:
            await initialize_services(config)
            yield
        finally:
            # initialize_services may fail after creating some services.
            # Always attempt cleanup so partially initialized services do not
            # leave background tasks, sockets, or other resources running.
            await shutdown_services()
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

    # Keep the configuration available to routes and extensions.
    app.state.config = config

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, dependencies=[Depends(verify_token)])
    app.include_router(ws_router)

    # Health check (no auth required)
    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "version": config.settings.version,
            "mode": "paper",
        }

    # Where the built dashboard lives (npm run build in src/frontend)
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

    # Serve frontend static files (when built)
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
