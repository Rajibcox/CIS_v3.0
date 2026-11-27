#!/usr/bin/env python3
"""
QUANTUM TRADER V1 - Main Application Entry Point
Professional Quantitative Futures Trading Platform
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from fastapi import WebSocket
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api.server import create_app
from src.backend.services import get_service_container
from src.backend.utils.config import Config

# Global configuration
config = Config()


def create_app_with_services():
    """Create the FastAPI application; service lifecycle is owned by server lifespan."""
    app = create_app(config)

    # CORS is also configured by create_app. Keep one authoritative policy there.
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        container = get_service_container()
        if container and container.websocket_manager:
            await container.websocket_manager.handle_websocket(websocket)
        else:
            await websocket.close(code=1011)

    return app


def main():
    """Main application entry point."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting QUANTUM TRADER V1...")
        logger.info(
            "Configuration: %s v%s",
            config.settings.app_name,
            config.settings.version,
        )

        uvicorn_config = {
            "app": create_app_with_services(),
            "host": config.settings.host,
            "port": config.settings.port,
            "log_level": config.settings.log_level.lower(),
            "reload": config.settings.debug,
        }

        if config.settings.ssl_enabled:
            uvicorn_config.update(
                {
                    "ssl_keyfile": config.settings.ssl_keyfile,
                    "ssl_certfile": config.settings.ssl_certfile,
                }
            )

        logger.info(
            "Starting server on %s:%s",
            config.settings.host,
            config.settings.port,
        )
        uvicorn.run(**uvicorn_config)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception:
        logger.exception("Fatal error")
        raise


if __name__ == "__main__":
    main()
