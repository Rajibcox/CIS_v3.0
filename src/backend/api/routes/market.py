"""
Market Intelligence API Routes for QUANTUM TRADER V1
Market overview, scanner, LONG/SHORT opportunities
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

router = APIRouter(prefix="/api/v1/market", tags=["market"])


# Enums
class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    SIDEWAYS = "sideways"


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


# Models
class MarketOverview(BaseModel):
    btc_dominance: float
    fear_greed_index: int
    fear_greed_label: str
    total_volume_24h: float
    total_open_interest: float
    funding_rate_avg: float
    top_gainer: Dict[str, Any]
    top_loser: Dict[str, Any]
    top_volume: Dict[str, Any]
    liquidations_24h: Dict[str, float]
    timestamp: datetime


class SymbolSnapshot(BaseModel):
    symbol: str
    exchange: str
    price: float
    change_24h_pct: float
    volume_24h: float
    volume_change_24h_pct: float
    open_interest: float
    oi_change_24h_pct: float
    funding_rate: float
    next_funding_time: datetime
    spread_bps: float
    spread_pct: float
    atr: float
    atr_pct: float
    volatility_24h: float
    regime: MarketRegime
    btc_correlation: float
    timestamp: datetime


class ScannerResult(BaseModel):
    symbol: str
    exchange: str
    direction: SignalDirection
    strategy: str
    timeframe: str
    signal_score: float
    regime: MarketRegime
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    risk_reward: float
    suggested_leverage: float
    position_quantity: float
    notional: float
    required_margin: float
    htf_alignment: bool
    btc_alignment: bool
    expires_at: datetime
    created_at: datetime


class OpportunityResponse(BaseModel):
    opportunities: List[ScannerResult]
    total_scanned: int
    scan_duration_ms: int
    timestamp: datetime


# Mock data generators
async def get_market_overview() -> MarketOverview:
    return MarketOverview(
        btc_dominance=52.3,
        fear_greed_index=65,
        fear_greed_label="Greed",
        total_volume_24h=125_000_000_000,
        total_open_interest=45_000_000_000,
        funding_rate_avg=0.0001,
        top_gainer={"symbol": "SOLUSDT", "change_pct": 12.5, "price": 145.32},
        top_loser={"symbol": "APEUSDT", "change_pct": -8.2, "price": 1.23},
        top_volume={"symbol": "BTCUSDT", "volume": 25_000_000_000},
        liquidations_24h={"long": 125_000_000, "short": 89_000_000},
        timestamp=datetime.utcnow()
    )


async def get_symbol_snapshot(symbol: str, exchange: str = "binance") -> SymbolSnapshot:
    return SymbolSnapshot(
        symbol=symbol,
        exchange=exchange,
        price=45000.0 if "BTC" in symbol else 3000.0,
        change_24h_pct=2.5,
        volume_24h=1_000_000_000,
        volume_change_24h_pct=15.0,
        open_interest=500_000_000,
        oi_change_24h_pct=5.0,
        funding_rate=0.0001,
        next_funding_time=datetime.utcnow(),
        spread_bps=2.0,
        spread_pct=0.02,
        atr=500.0,
        atr_pct=1.1,
        volatility_24h=3.5,
        regime=MarketRegime.TRENDING,
        btc_correlation=0.85,
        timestamp=datetime.utcnow()
    )


async def run_market_scan(
    exchanges: Optional[List[str]] = None,
    timeframes: Optional[List[str]] = None,
    min_score: float = 0.7,
    max_results: int = 50
) -> OpportunityResponse:
    """Run market scanner"""
    # Mock results
    opportunities = [
        ScannerResult(
            symbol="BTCUSDT",
            exchange="binance",
            direction=SignalDirection.LONG,
            strategy="Trend Following",
            timeframe="1h",
            signal_score=85.5,
            regime=MarketRegime.TRENDING,
            entry_price=45100.0,
            stop_loss=44200.0,
            tp1=46000.0,
            tp2=47000.0,
            tp3=48500.0,
            risk_reward=3.2,
            suggested_leverage=3.0,
            position_quantity=0.01,
            notional=451.0,
            required_margin=150.3,
            htf_alignment=True,
            btc_alignment=True,
            expires_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        ),
        ScannerResult(
            symbol="ETHUSDT",
            exchange="binance",
            direction=SignalDirection.LONG,
            strategy="Breakout",
            timeframe="4h",
            signal_score=78.0,
            regime=MarketRegime.BREAKOUT,
            entry_price=3050.0,
            stop_loss=2950.0,
            tp1=3200.0,
            tp2=3350.0,
            tp3=3550.0,
            risk_reward=2.8,
            suggested_leverage=3.0,
            position_quantity=0.1,
            notional=305.0,
            required_margin=101.7,
            htf_alignment=True,
            btc_alignment=True,
            expires_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        ),
        ScannerResult(
            symbol="SOLUSDT",
            exchange="bitget",
            direction=SignalDirection.SHORT,
            strategy="Mean Reversion",
            timeframe="15m",
            signal_score=72.5,
            regime=MarketRegime.RANGING,
            entry_price=148.0,
            stop_loss=152.0,
            tp1=142.0,
            tp2=138.0,
            tp3=133.0,
            risk_reward=2.5,
            suggested_leverage=2.0,
            position_quantity=2.0,
            notional=296.0,
            required_margin=148.0,
            htf_alignment=False,
            btc_alignment=False,
            expires_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
    ]

    return OpportunityResponse(
        opportunities=opportunities[:max_results],
        total_scanned=150,
        scan_duration_ms=1250,
        timestamp=datetime.utcnow()
    )


# Routes
@router.get("/overview", response_model=MarketOverview)
async def get_market_overview_route():
    """Get market overview"""
    return await get_market_overview()


@router.get("/symbol/{symbol}", response_model=SymbolSnapshot)
async def get_symbol(symbol: str, exchange: str = Query("binance", regex="^(binance|bitget)$")):
    """Get detailed symbol snapshot"""
    return await get_symbol_snapshot(symbol.upper(), exchange)


@router.get("/scanner/scan", response_model=OpportunityResponse)
async def scan_markets(
    exchanges: Optional[str] = Query(None, description="Comma-separated: binance,bitget"),
    timeframes: Optional[str] = Query(None, description="Comma-separated: 15m,1h,4h"),
    min_score: float = Query(0.7, ge=0, le=100),
    max_results: int = Query(50, ge=1, le=200)
):
    """Run market scan for opportunities"""
    exch_list = exchanges.split(",") if exchanges else ["binance", "bitget"]
    tf_list = timeframes.split(",") if timeframes else ["15m", "1h", "4h"]
    return await run_market_scan(exch_list, tf_list, min_score, max_results)


@router.get("/opportunities/long", response_model=OpportunityResponse)
async def get_long_opportunities(
    min_score: float = Query(0.7, ge=0, le=100),
    max_results: int = Query(20, ge=1, le=100)
):
    """Get LONG opportunities"""
    result = await run_market_scan(min_score=min_score, max_results=max_results)
    result.opportunities = [o for o in result.opportunities if o.direction == SignalDirection.LONG]
    return result


@router.get("/opportunities/short", response_model=OpportunityResponse)
async def get_short_opportunities(
    min_score: float = Query(0.7, ge=0, le=100),
    max_results: int = Query(20, ge=1, le=100)
):
    """Get SHORT opportunities"""
    result = await run_market_scan(min_score=min_score, max_results=max_results)
    result.opportunities = [o for o in result.opportunities if o.direction == SignalDirection.SHORT]
    return result


@router.get("/regime")
async def get_market_regime():
    """Get current market regime analysis"""
    return {
        "btc_regime": "trending",
        "altcoin_regime": "ranging",
        "volatility_state": "normal",
        "trend_strength": 65,
        "key_levels": {
            "btc_support": 42000,
            "btc_resistance": 48000,
            "eth_support": 2800,
            "eth_resistance": 3200
        },
        "correlation_matrix": {
            "BTC_ETH": 0.85,
            "BTC_SOL": 0.72,
            "ETH_SOL": 0.78
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/funding")
async def get_funding_rates():
    """Get current funding rates"""
    return {
        "rates": [
            {"symbol": "BTCUSDT", "exchange": "binance", "rate": 0.0001, "next_funding": "2026-11-27T00:00:00Z"},
            {"symbol": "ETHUSDT", "exchange": "binance", "rate": 0.0002, "next_funding": "2026-11-27T00:00:00Z"},
            {"symbol": "SOLUSDT", "exchange": "bitget", "rate": -0.0001, "next_funding": "2026-11-27T00:00:00Z"},
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/open-interest")
async def get_open_interest():
    """Get open interest data"""
    return {
        "data": [
            {"symbol": "BTCUSDT", "exchange": "binance", "oi": 5_000_000_000, "change_24h_pct": 3.2},
            {"symbol": "ETHUSDT", "exchange": "binance", "oi": 3_200_000_000, "change_24h_pct": 5.1},
            {"symbol": "SOLUSDT", "exchange": "bitget", "oi": 800_000_000, "change_24h_pct": -2.3},
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/liquidations")
async def get_liquidations():
    """Get recent liquidations"""
    return {
        "data": [
            {"symbol": "BTCUSDT", "side": "LONG", "quantity": 12.5, "price": 44800, "time": "2026-11-26T15:30:00Z"},
            {"symbol": "ETHUSDT", "side": "SHORT", "quantity": 85.0, "price": 2980, "time": "2026-11-26T15:25:00Z"},
        ],
        "total_24h": {"long": 125_000_000, "short": 89_000_000},
        "timestamp": datetime.utcnow().isoformat()
    }