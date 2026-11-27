"""
Historical Data Service for QUANTUM TRADER V1
Manages historical market data storage, retrieval, and backfill operations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from sqlalchemy.exc import IntegrityError

from src.backend.models.database import (
    Symbol, MarketCandle, Exchange, MarketRegime
)
from src.backend.services.market_data_service import MarketDataService, CandleData
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger, log_service_event


logger = get_logger(__name__)


@dataclass
class DataQualityReport:
    """Report on data quality for a symbol/timeframe"""
    symbol: str
    timeframe: str
    total_candles: int
    missing_candles: int
    duplicate_candles: int
    gaps: List[Tuple[datetime, datetime]]
    start_date: datetime
    end_date: datetime
    quality_score: float  # 0-100


@dataclass
class BackfillJob:
    """Backfill job specification"""
    symbol: str
    exchange: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    priority: int = 1
    status: str = "pending"
    progress: float = 0.0
    error: Optional[str] = None


class HistoricalDataService:
    """Service for managing historical market data"""

    def __init__(self, config: Config, market_data_service: MarketDataService):
        self.config = config
        self.market_data_service = market_data_service
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._backfill_task: Optional[asyncio.Task] = None
        self._backfill_queue: asyncio.Queue = asyncio.Queue()
        self._active_jobs: Dict[str, BackfillJob] = {}
        self._completed_jobs: List[BackfillJob] = []

    async def initialize(self):
        """Initialize historical data service"""
        self.logger.info("Initializing Historical Data Service...")
        self._running = True
        if self._backfill_task is None or self._backfill_task.done():
            self._backfill_task = asyncio.create_task(self._process_backfill_queue())
        self.logger.info("Historical Data Service initialized")

    async def shutdown(self):
        """Shutdown service"""
        self.logger.info("Shutting down Historical Data Service...")
        self._running = False
        if self._backfill_task is not None:
            self._backfill_task.cancel()
            try:
                await self._backfill_task
            except asyncio.CancelledError:
                pass
            finally:
                self._backfill_task = None

    async def store_candles(self, db: Session, candles: List[CandleData]) -> Tuple[int, int]:
        """Store candles in database with deduplication"""
        inserted = 0
        updated = 0

        for candle in candles:
            try:
                symbol = db.query(Symbol).join(Exchange).filter(
                    and_(
                        Symbol.symbol == candle.symbol,
                        Exchange.name == candle.exchange
                    )
                ).first()

                if not symbol:
                    exchange = db.query(Exchange).filter(Exchange.name == candle.exchange).first()
                    if not exchange:
                        self.logger.warning(f"Exchange {candle.exchange} not found for {candle.symbol}")
                        continue

                    symbol = Symbol(
                        exchange_id=exchange.id,
                        symbol=candle.symbol,
                        base_asset=candle.symbol[:-4],
                        quote_asset="USDT",
                        is_active=True,
                        is_eligible=True
                    )
                    db.add(symbol)
                    db.flush()

                existing = db.query(MarketCandle).filter(
                    and_(
                        MarketCandle.symbol_id == symbol.id,
                        MarketCandle.timeframe == candle.timeframe,
                        MarketCandle.open_time == candle.open_time
                    )
                ).first()

                if existing:
                    existing.open = float(candle.open)
                    existing.high = float(candle.high)
                    existing.low = float(candle.low)
                    existing.close = float(candle.close)
                    existing.volume = float(candle.volume)
                    existing.quote_volume = float(candle.quote_volume) if candle.quote_volume else None
                    existing.trades = candle.trades
                    existing.is_closed = candle.is_closed
                    updated += 1
                else:
                    new_candle = MarketCandle(
                        symbol_id=symbol.id,
                        timeframe=candle.timeframe,
                        open_time=candle.open_time,
                        open=float(candle.open),
                        high=float(candle.high),
                        low=float(candle.low),
                        close=float(candle.close),
                        volume=float(candle.volume),
                        quote_volume=float(candle.quote_volume) if candle.quote_volume else None,
                        trades=candle.trades,
                        is_closed=candle.is_closed
                    )
                    db.add(new_candle)
                    inserted += 1

            except IntegrityError:
                db.rollback()
                self.logger.warning(f"Integrity error storing candle for {candle.symbol}")
                continue
            except Exception as e:
                self.logger.error(f"Error storing candle for {candle.symbol}: {e}")
                continue

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error committing candles: {e}")
            raise

        return inserted, updated

    async def get_candles(
        self,
        db: Session,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        exchange: Optional[str] = None
    ) -> List[MarketCandle]:
        query = db.query(MarketCandle).join(Symbol).join(Exchange).filter(
            and_(
                Symbol.symbol == symbol,
                MarketCandle.timeframe == timeframe
            )
        )

        if exchange:
            query = query.filter(Exchange.name == exchange)

        if start_time:
            query = query.filter(MarketCandle.open_time >= start_time)

        if end_time:
            query = query.filter(MarketCandle.open_time <= end_time)

        query = query.order_by(MarketCandle.open_time.desc()).limit(limit)
        return query.all()

    async def get_latest_candle(
        self,
        db: Session,
        symbol: str,
        timeframe: str,
        exchange: Optional[str] = None
    ) -> Optional[MarketCandle]:
        query = db.query(MarketCandle).join(Symbol).join(Exchange).filter(
            and_(
                Symbol.symbol == symbol,
                MarketCandle.timeframe == timeframe
            )
        )

        if exchange:
            query = query.filter(Exchange.name == exchange)

        return query.order_by(MarketCandle.open_time.desc()).first()

    async def check_data_quality(
        self,
        db: Session,
        symbol: str,
        timeframe: str,
        exchange: Optional[str] = None,
        lookback_days: int = 30
    ) -> DataQualityReport:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=lookback_days)

        candles = await self.get_candles(db, symbol, timeframe, start_time, end_time, exchange=exchange)

        if not candles:
            return DataQualityReport(
                symbol=symbol,
                timeframe=timeframe,
                total_candles=0,
                missing_candles=0,
                duplicate_candles=0,
                gaps=[],
                start_date=start_time,
                end_date=end_time,
                quality_score=0.0
            )

        tf_minutes = self._timeframe_to_minutes(timeframe)
        expected_candles = int((lookback_days * 24 * 60) / tf_minutes)

        gaps = []
        sorted_candles = sorted(candles, key=lambda c: c.open_time)
        for i in range(1, len(sorted_candles)):
            expected_time = sorted_candles[i-1].open_time + timedelta(minutes=tf_minutes)
            actual_time = sorted_candles[i].open_time
            if actual_time > expected_time + timedelta(minutes=1):
                gaps.append((expected_time, actual_time))

        seen_times = set()
        duplicate_count = 0
        for c in candles:
            if c.open_time in seen_times:
                duplicate_count += 1
            seen_times.add(c.open_time)

        missing_count = max(0, expected_candles - len(candles) + duplicate_count)
        quality_score = max(0, 100 - (missing_count / expected_candles * 100) - (len(gaps) * 5) - (duplicate_count * 2))

        return DataQualityReport(
            symbol=symbol,
            timeframe=timeframe,
            total_candles=len(candles),
            missing_candles=missing_count,
            duplicate_candles=duplicate_count,
            gaps=gaps,
            start_date=sorted_candles[0].open_time if sorted_candles else start_time,
            end_date=sorted_candles[-1].open_time if sorted_candles else end_time,
            quality_score=max(0, min(100, quality_score))
        )

    def _timeframe_to_minutes(self, timeframe: str) -> int:
        mapping = {
            "3m": 3, "5m": 5, "15m": 15,
            "1h": 60, "4h": 240, "1d": 1440
        }
        return mapping.get(timeframe, 60)

    async def schedule_backfill(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        priority: int = 1
    ) -> str:
        job_id = f"{exchange}_{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        job = BackfillJob(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            priority=priority
        )
        self._active_jobs[job_id] = job
        await self._backfill_queue.put(job)
        self.logger.info(f"Scheduled backfill job: {job_id}")
        return job_id

    async def _process_backfill_queue(self):
        while self._running:
            try:
                job = await asyncio.wait_for(self._backfill_queue.get(), timeout=5.0)
                await self._execute_backfill(job)
                self._completed_jobs.append(job)
                if hasattr(job, 'job_id'):
                    del self._active_jobs[job.job_id]
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing backfill queue: {e}")

    async def _execute_backfill(self, job: BackfillJob):
        job.status = "running"
        self.logger.info(f"Starting backfill: {job.symbol} {job.timeframe} {job.exchange}")

        try:
            adapter = self.market_data_service.adapters.get(job.exchange)
            if not adapter:
                raise ValueError(f"Exchange {job.exchange} not available")

            current = job.start_date
            total_days = (job.end_date - job.start_date).days
            processed = 0

            while current < job.end_date and self._running:
                end_chunk = min(current + timedelta(days=7), job.end_date)

                candles = await adapter.fetch_candles(
                    job.symbol,
                    job.timeframe,
                    limit=1000,
                    since=int(current.timestamp() * 1000)
                )

                filtered_candles = [
                    c for c in candles
                    if current <= c.open_time <= end_chunk
                ]

                if filtered_candles:
                    pass

                processed += len(filtered_candles)
                job.progress = min(100, (processed / max(1, total_days * 100)) * 100)
                current = end_chunk

                await asyncio.sleep(0.1)

            job.status = "completed"
            job.progress = 100
            self.logger.info(f"Completed backfill: {job.symbol} - {processed} candles")

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            self.logger.error(f"Backfill failed for {job.symbol}: {e}")
            raise

    async def get_backfill_status(self, job_id: str) -> Optional[BackfillJob]:
        if job_id in self._active_jobs:
            return self._active_jobs[job_id]
        for job in self._completed_jobs:
            if hasattr(job, "job_id") and job.job_id == job_id:
                return job
        return None

    async def get_symbol_coverage(
        self,
        db: Session,
        symbol: str,
        timeframe: str,
        exchange: Optional[str] = None
    ) -> Dict[str, Any]:
        earliest = db.query(MarketCandle).join(Symbol).join(Exchange).filter(
            and_(
                Symbol.symbol == symbol,
                MarketCandle.timeframe == timeframe
            )
        )
        if exchange:
            earliest = earliest.filter(Exchange.name == exchange)

        earliest_candle = earliest.order_by(MarketCandle.open_time.asc()).first()
        latest_candle = earliest.order_by(MarketCandle.open_time.desc()).first()
        total_count = earliest.count()

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "exchange": exchange,
            "total_candles": total_count,
            "earliest_date": earliest_candle.open_time if earliest_candle else None,
            "latest_date": latest_candle.open_time if latest_candle else None,
            "date_range_days": (
                (latest_candle.open_time - earliest_candle.open_time).days
                if earliest_candle and latest_candle else 0
            )
        }

    async def cleanup_old_data(
        self,
        db: Session,
        retention_days: int = 90
    ) -> int:
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        deleted = db.query(MarketCandle).filter(
            MarketCandle.open_time < cutoff
        ).delete(synchronize_session=False)

        db.commit()
        self.logger.info(f"Cleaned up {deleted} candles older than {retention_days} days")
        return deleted

    async def shutdown(self):
        self._running = False


async def create_historical_data_service(
    config: Config,
    market_data_service: MarketDataService
) -> HistoricalDataService:
    service = HistoricalDataService(config, market_data_service)
    await service.initialize()
    return service
