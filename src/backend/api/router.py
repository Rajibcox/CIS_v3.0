"""
Main API Router for QUANTUM TRADER V1
Combines all route modules
"""

from fastapi import APIRouter

from src.backend.api.routes import overview, market, signals, strategies, trading, config, analytics, system

# Main API router
# Each route module already declares its own /api/v1/<name> prefix
api_router = APIRouter()

# Include all route modules
api_router.include_router(overview.router)
api_router.include_router(market.router)
api_router.include_router(signals.router)
api_router.include_router(strategies.router)
api_router.include_router(trading.router)
api_router.include_router(config.router)
api_router.include_router(analytics.router)
api_router.include_router(system.router)


# WebSocket router (for real-time updates)
ws_router = APIRouter(prefix="/ws")

@ws_router.get("/dashboard")
async def dashboard_websocket():
    """WebSocket endpoint for real-time dashboard updates"""
    # This would be implemented with websockets library
    return {"message": "WebSocket endpoint - upgrade required"}


@ws_router.get("/market-data")
async def market_data_websocket():
    """WebSocket endpoint for real-time market data"""
    return {"message": "WebSocket endpoint - upgrade required"}


@ws_router.get("/positions")
async def positions_websocket():
    """WebSocket endpoint for real-time position updates"""
    return {"message": "WebSocket endpoint - upgrade required"}


@ws_router.get("/signals")
async def signals_websocket():
    """WebSocket endpoint for real-time signal updates"""
    return {"message": "WebSocket endpoint - upgrade required"}