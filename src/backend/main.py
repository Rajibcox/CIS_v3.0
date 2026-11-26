#!/usr/bin/env python3
"""
QUANTUM TRADER V1 - Main Application Entry Point
Professional Quantitative Futures Trading Platform
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.backend.api.server import create_app
from src.backend.utils.config import Config
from src.backend.utils.logger import setup_logging
from src.backend.services import initialize_services, shutdown_services, get_service_container

# Global configuration
config = Config()

# Global service container
_service_container = None


async def initialize_services():
    """Initialize all services using service container"""
    global _service_container

    # Setup logging
    setup_logging(config.settings.log_level)
    logger = logging.getLogger(__name__)

    logger.info("Initializing QUANTUM TRADER V1 services...")

    # Initialize all services via container
    _service_container = await initialize_services(config)

    logger.info("All services initialized successfully")


async def shutdown_services():
    """Gracefully shutdown all services"""
    logger = logging.getLogger(__name__)

    logger.info("Shutting down QUANTUM TRADER V1 services...")

    if _service_container:
        await _service_container.shutdown_all()

    logger.info("All services shutdown successfully")


def create_app_with_services():
    """Create FastAPI app with services initialized"""
    app = create_app(config)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        await initialize_services()

    @app.on_event("shutdown")
    async def shutdown_event():
        await shutdown_services()

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        container = get_service_container()
        if container and container.websocket_manager:
            await container.websocket_manager.handle_websocket(websocket)
        else:
            await websocket.close(code=1011)

    return app


def main():
    """Main application entry point"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting QUANTUM TRADER V1...")
        logger.info(f"Configuration: {config.settings.app_name} v{config.settings.version}")

        # Create and run the application
        app = create_app_with_services()

        # Run the application
        uvicorn_config = {
            "app": app,
            "host": config.settings.host,
            "port": config.settings.port,
            "log_level": config.settings.log_level.lower(),
            "reload": config.settings.debug,
        }

        if config.settings.ssl_enabled:
            uvicorn_config.update({
                "ssl_keyfile": config.settings.ssl_keyfile,
                "ssl_certfile": config.settings.ssl_certfile,
            })

        logger.info(f"Starting server on {config.settings.host}:{config.settings.port}")
        import uvicorn
        uvicorn.run(**uvicorn_config)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure services are shutdown
        asyncio.run(shutdown_services())


if __name__ == "__main__":
    main()