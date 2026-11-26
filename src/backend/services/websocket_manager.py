"""
WebSocket Manager for QUANTUM TRADER V1
Handles real-time WebSocket connections for market data and trade updates
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from src.backend.utils.config import Config
from src.backend.utils.logger import get_logger


logger = logging.getLogger(__name__)


class ChannelType(Enum):
    """WebSocket channel types"""
    TICKER = "ticker"
    CANDLE = "candle"
    ORDERBOOK = "orderbook"
    TRADE = "trade"
    POSITION = "position"
    SIGNAL = "signal"
    TP_SL = "tp_sl"
    PNL = "pnl"
    SYSTEM = "system"
    MARKET_OVERVIEW = "market_overview"
    FUNDING = "funding"
    REGIME = "regime"


@dataclass
class Subscription:
    """WebSocket subscription"""
    client_id: str
    channel: str
    params: Dict = field(default_factory=dict)
    subscribed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WSMessage:
    """WebSocket message structure"""
    type: str
    channel: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "channel": self.channel,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id
        }, default=str)


class ConnectionManager:
    """Manages WebSocket connections and subscriptions"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Active connections: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

        # Client metadata
        self.client_info: Dict[str, Dict] = {}

        # Subscriptions: channel -> Set[client_id]
        self.subscriptions: Dict[str, Set[str]] = {}

        # Client subscriptions: client_id -> Set[channel]
        self.client_subscriptions: Dict[str, Set[str]] = {}

        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}

        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "errors": 0
        }

    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """Accept new WebSocket connection"""
        if client_id is None:
            client_id = str(uuid.uuid4())[:8]

        await websocket.accept()

        self.active_connections[client_id] = websocket
        self.client_info[client_id] = {
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow(),
            "subscriptions": set(),
            "ip": websocket.client.host if websocket.client else "unknown"
        }
        self.client_subscriptions[client_id] = set()

        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.active_connections)

        # Send welcome message
        await self.send_personal(client_id, WSMessage(
            type="welcome",
            channel="system",
            data={
                "client_id": client_id,
                "server_time": datetime.utcnow().isoformat(),
                "server_version": "1.0.0",
                "supported_channels": [c.value for c in ChannelType]
            }
        ))

        self.logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        return client_id

    async def disconnect(self, client_id: str):
        """Disconnect client and clean up"""
        if client_id in self.active_connections:
            # Remove from all subscriptions
            if client_id in self.client_subscriptions:
                for channel in self.client_subscriptions[client_id]:
                    if channel in self.subscriptions:
                        self.subscriptions[channel].discard(client_id)

            # Clean up
            del self.active_connections[client_id]
            del self.client_info[client_id]
            if client_id in self.client_subscriptions:
                del self.client_subscriptions[client_id]

            self.stats["active_connections"] = len(self.active_connections)
            self.logger.info(f"Client disconnected. Active connections: {len(self.active_connections)}")

    async def subscribe(self, client_id: str, channel: str, params: Dict = None) -> bool:
        """Subscribe client to channel"""
        if client_id not in self.active_connections:
            return False

        # Validate channel
        try:
            channel_type = ChannelType(channel)
        except ValueError:
            # Allow custom channels
            pass

        # Add to subscriptions
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()
        self.subscriptions[channel].add(client_id)
        self.client_subscriptions[client_id].add(channel)

        # Update client info
        if client_id in self.client_info:
            self.client_info[client_id]["subscriptions"].add(channel)

        # Send confirmation
        await self.send_personal(client_id, WSMessage(
            type="subscribed",
            channel=channel,
            data={"channel": channel, "params": params or {}}
        ))

        self.logger.info(f"Client subscribed to {channel}")
        return True

    async def unsubscribe(self, client_id: str, channel: str) -> bool:
        """Unsubscribe client from channel"""
        if client_id not in self.active_connections:
            return False

        if channel in self.subscriptions:
            self.subscriptions[channel].discard(client_id)

        if client_id in self.client_subscriptions:
            self.client_subscriptions[client_id].discard(channel)

        if client_id in self.client_info:
            self.client_info[client_id]["subscriptions"].discard(channel)

        await self.send_personal(client_id, WSMessage(
            type="unsubscribed",
            channel=channel,
            data={"channel": channel}
        ))

        return True

    async def send_personal(self, client_id: str, message: WSMessage) -> bool:
        """Send message to specific client"""
        if client_id not in self.active_connections:
            return False

        try:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message.to_json())
            self.stats["total_messages_sent"] += 1
            return True
        except Exception as e:
            logging.getLogger(__name__).error(f"Error sending to client {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def broadcast(self, channel: str, message: WSMessage, exclude: List[str] = None) -> int:
        """Broadcast message to all subscribers of a channel"""
        if channel not in self.subscriptions:
            return 0

        exclude_set = set(exclude or [])
        sent = 0

        for client_id in list(self.subscriptions[channel]):
            if client_id in exclude_set:
                continue
            if await self.send_personal(client_id, message):
                sent += 1

        return sent

    async def broadcast_to_all(self, message: WSMessage, exclude: List[str] = None) -> int:
        """Broadcast message to all connected clients"""
        exclude_set = set(exclude or [])
        sent = 0

        for client_id in list(self.active_connections.keys()):
            if client_id in exclude_set:
                continue
            if await self.send_personal(client_id, message):
                sent += 1

        return sent

    async def handle_message(self, client_id: str, message: Dict):
        """Handle incoming WebSocket message"""
        if client_id not in self.active_connections:
            return

        self.stats["total_messages_received"] += 1

        msg_type = message.get("type", "")
        channel = message.get("channel", "")
        request_id = message.get("request_id")

        # Update last activity
        if client_id in self.client_info:
            self.client_info[client_id]["last_ping"] = datetime.utcnow()

        # Handle built-in message types
        if msg_type == "subscribe":
            channel = message.get("channel", "")
            params = message.get("params", {})
            await self.subscribe(client_id, channel, params)

        elif msg_type == "unsubscribe":
            channel = message.get("channel", "")
            await self.unsubscribe(client_id, channel)

        elif msg_type == "ping":
            await self.send_personal(client_id, WSMessage(
                type="pong",
                channel="system",
                data={"timestamp": datetime.utcnow().isoformat()},
                request_id=request_id
            ))

        elif msg_type == "get_stats":
            await self.send_personal(client_id, WSMessage(
                type="stats",
                channel="system",
                data=self.get_stats(),
                request_id=request_id
            ))

        elif msg_type == "get_channels":
            await self.send_personal(client_id, WSMessage(
                type="channels",
                channel="system",
                data={
                    "subscribed": list(self.client_subscriptions.get(client_id, [])),
                    "available": [c.value for c in ChannelType]
                },
                request_id=request_id
            ))

        # Call custom handler if registered
        handler_key = f"{msg_type}:{channel}" if channel else msg_type
        if handler_key in self.message_handlers:
            try:
                await self.message_handlers[handler_key](client_id, message)
            except Exception as e:
                logging.getLogger(__name__).error(f"Handler error: {e}")

    async def handle_connection(self, websocket: WebSocket, client_id: str = None):
        """Handle WebSocket connection lifecycle"""
        client_id = await self.connect(websocket, client_id)

        try:
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self.handle_message(client_id, message)
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await self.send_personal(client_id, WSMessage(
                        type="error",
                        channel="system",
                        data={"error": "Invalid JSON format"}
                    ))
                except Exception as e:
                    logging.getLogger(__name__).error(f"Error handling message: {e}")
                    break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logging.getLogger(__name__).error(f"Connection error: {e}")
        finally:
            await self.disconnect(client_id)

    def register_handler(self, message_type: str, channel: str, handler: Callable):
        """Register custom message handler"""
        key = f"{message_type}:{channel}" if channel else message_type
        self.message_handlers[key] = handler

    def get_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            **self.stats,
            "active_connections": len(self.active_connections),
            "total_subscriptions": sum(len(s) for s in self.subscriptions.values()),
            "channels_active": len([c for c, s in self.subscriptions.items() if s]),
            "clients": {
                cid: {
                    "connected_at": info["connected_at"].isoformat(),
                    "subscriptions": list(info["subscriptions"]),
                    "ip": info.get("ip", "unknown")
                }
                for cid, info in self.client_info.items()
            }
        }

    def get_channel_subscribers(self, channel: str) -> List[str]:
        """Get list of clients subscribed to channel"""
        return list(self.subscriptions.get(channel, set()))

    def is_subscribed(self, client_id: str, channel: str) -> bool:
        """Check if client is subscribed to channel"""
        return client_id in self.subscriptions.get(channel, set())


class WebSocketManager:
    """High-level WebSocket manager integrating with services"""

    def __init__(self, config: Config, market_data_service=None, tp_sl_service=None,
                 signal_service=None, execution_service=None, pnl_service=None):
        self.config = config
        self.connection_manager = ConnectionManager(config)
        self.logger = logging.getLogger(__name__)

        # Service references
        self.market_data_service = market_data_service
        self.tp_sl_service = tp_sl_service
        self.signal_service = signal_service
        self.execution_service = execution_service
        self.pnl_service = pnl_service

        self._running = False
        self._update_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize WebSocket manager"""
        self.logger.info("Initializing WebSocket Manager...")

        # Register custom handlers
        self.connection_manager.register_handler("get_ticker", "market", self._handle_get_ticker)
        self.connection_manager.register_handler("get_orderbook", "market", self._handle_get_orderbook)
        self.connection_manager.register_handler("get_position", "trading", self._handle_get_position)
        self.connection_manager.register_handler("get_signal", "signals", self._handle_get_signal)
        self.connection_manager.register_handler("get_pnl", "pnl", self._handle_get_pnl)

        # Start background update task
        self._running = True
        asyncio.create_task(self._broadcast_updates())

        self.logger.info("WebSocket Manager initialized")

    async def shutdown(self):
        """Shutdown WebSocket manager"""
        self._running = False
        # Disconnect all clients
        for client_id in list(self.connection_manager.active_connections.keys()):
            await self.connection_manager.disconnect(client_id)
        self.logger.info("WebSocket Manager shut down")

    async def handle_websocket(self, websocket, client_id: str = None):
        """Handle incoming WebSocket connection"""
        await self.connection_manager.handle_connection(websocket)

    # Market data broadcasting
    async def broadcast_ticker(self, symbol: str, ticker_data: dict, exchange: str = "binance"):
        """Broadcast ticker update"""
        message = WSMessage(
            type="update",
            channel=f"ticker:{symbol}",
            data={
                "symbol": symbol,
                "exchange": exchange,
                **ticker_data
            }
        )
        await self.connection_manager.broadcast(f"ticker:{symbol}", message)

    async def broadcast_candle(self, symbol: str, timeframe: str, candle_data: dict, exchange: str = "binance"):
        """Broadcast candle update"""
        message = WSMessage(
            type="update",
            channel=f"candle:{symbol}:{timeframe}",
            data={
                "symbol": symbol,
                "timeframe": timeframe,
                "exchange": exchange,
                **candle_data
            }
        )
        await self.connection_manager.broadcast(f"candle:{symbol}:{timeframe}", message)

    async def broadcast_orderbook(self, symbol: str, orderbook_data: dict, exchange: str = "binance"):
        """Broadcast orderbook update"""
        message = WSMessage(
            type="update",
            channel=f"orderbook:{symbol}",
            data={
                "symbol": symbol,
                "exchange": exchange,
                **orderbook_data
            }
        )
        await self.connection_manager.broadcast(f"orderbook:{symbol}", message)

    async def broadcast_trade(self, trade_data: dict):
        """Broadcast trade execution"""
        message = WSMessage(
            type="trade",
            channel="trade",
            data=trade_data
        )
        await self.connection_manager.broadcast("trade", message)

    async def broadcast_position_update(self, position_data: dict):
        """Broadcast position update"""
        message = WSMessage(
            type="update",
            channel="position",
            data=position_data
        )
        await self.connection_manager.broadcast("position", message)

    async def broadcast_tp_sl_update(self, position_id: int, tp_sl_data: dict):
        """Broadcast TP/SL update"""
        message = WSMessage(
            type="update",
            channel=f"tp_sl:{position_id}",
            data={
                "position_id": position_id,
                **tp_sl_data
            }
        )
        await self.connection_manager.broadcast(f"tp_sl:{position_id}", message)

    async def broadcast_signal(self, signal_data: dict):
        """Broadcast new signal"""
        message = WSMessage(
            type="signal",
            channel="signal",
            data=signal_data
        )
        await self.connection_manager.broadcast("signal", message)

    async def broadcast_pnl_update(self, pnl_data: dict):
        """Broadcast PnL update"""
        message = WSMessage(
            type="update",
            channel="pnl",
            data=pnl_data
        )
        await self.connection_manager.broadcast("pnl", message)

    async def broadcast_system_status(self, status_data: dict):
        """Broadcast system status"""
        message = WSMessage(
            type="status",
            channel="system",
            data=status_data
        )
        await self.connection_manager.broadcast_to_all(message)

    async def broadcast_market_overview(self, overview_data: dict):
        """Broadcast market overview"""
        message = WSMessage(
            type="overview",
            channel="market_overview",
            data=overview_data
        )
        await self.connection_manager.broadcast("market_overview", message)

    async def broadcast_funding_update(self, symbol: str, funding_data: dict):
        """Broadcast funding rate update"""
        message = WSMessage(
            type="update",
            channel=f"funding:{symbol}",
            data={
                "symbol": symbol,
                **funding_data
            }
        )
        await self.connection_manager.broadcast(f"funding:{symbol}", message)

    async def broadcast_regime_change(self, symbol: str, regime_data: dict):
        """Broadcast market regime change"""
        message = WSMessage(
            type="regime_change",
            channel=f"regime:{symbol}",
            data={
                "symbol": symbol,
                **regime_data
            }
        )
        await self.connection_manager.broadcast(f"regime:{symbol}", message)

    async def _broadcast_updates(self):
        """Background task to broadcast periodic updates"""
        while True:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds

                # Broadcast market overview periodically
                # This would fetch from market data service

                # Broadcast system stats
                stats = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "uptime_seconds": 0,  # Would calculate actual uptime
                    "memory_usage_mb": 0,
                    "cpu_percent": 0
                }
                await self.broadcast_system_status(stats)

            except Exception as e:
                logging.getLogger(__name__).error(f"Error in broadcast updates: {e}")
            await asyncio.sleep(30)  # Update every 30 seconds

    # Message handlers for client requests
    async def _handle_get_ticker(self, client_id: str, message: Dict):
        """Handle get ticker request"""
        symbol = message.get("symbol", "BTCUSDT")
        exchange = message.get("exchange", "binance")

        # This would fetch from market data service
        ticker_data = {
            "symbol": symbol,
            "exchange": exchange,
            "price": 50000,
            "bid": 49999,
            "ask": 50001,
            "volume_24h": 1000000,
            "change_24h_pct": 2.5
        }

        await self.connection_manager.send_personal(
            client_id,
            WSMessage(
                type="ticker",
                channel=f"ticker:{symbol}",
                data=ticker_data,
                request_id=message.get("request_id")
            )
        )

    async def _handle_get_orderbook(self, client_id: str, message: Dict):
        """Handle get orderbook request"""
        symbol = message.get("symbol", "BTCUSDT")
        exchange = message.get("exchange", "binance")
        depth = message.get("depth", 20)

        # Would fetch from market data service
        orderbook_data = {
            "symbol": symbol,
            "exchange": exchange,
            "bids": [[50000, 1.0], [49999, 2.0]],
            "asks": [[50001, 1.0], [50002, 2.0]],
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.connection_manager.send_personal(
            client_id,
            WSMessage(
                type="orderbook",
                channel=f"orderbook:{symbol}",
                data=orderbook_data,
                request_id=message.get("request_id")
            )
        )

    async def _handle_get_position(self, client_id: str, message: Dict):
        """Handle get position request"""
        position_id = message.get("position_id")

        # Would fetch from execution service
        position_data = {
            "position_id": position_id,
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 50000,
            "quantity": 0.01,
            "unrealized_pnl": 50.0
        }

        await self.connection_manager.send_personal(
            client_id,
            WSMessage(
                type="position",
                channel="position",
                data=position_data,
                request_id=message.get("request_id")
            )
        )

    async def _handle_get_signal(self, client_id: str, message: Dict):
        """Handle get signal request"""
        signal_id = message.get("signal_id")

        # Would fetch from signal service
        signal_data = {
            "signal_id": signal_id,
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 50000,
            "stop_loss": 49000,
            "tp1": 51000,
            "tp2": 52000,
            "tp3": 53000
        }

        await self.connection_manager.send_personal(
            client_id,
            WSMessage(
                type="signal",
                channel="signal",
                data=signal_data,
                request_id=message.get("request_id")
            )
        )

    async def _handle_get_pnl(self, client_id: str, message: Dict):
        """Handle get PnL request"""
        period = message.get("period", "30d")

        # Would fetch from PnL service
        pnl_data = {
            "period": period,
            "net_pnl": 150.50,
            "win_rate": 65.5,
            "profit_factor": 1.8,
            "total_trades": 47
        }

        await self.connection_manager.send_personal(
            client_id,
            WSMessage(
                type="pnl",
                channel="pnl",
                data=pnl_data,
                request_id=message.get("request_id")
            )
        )


async def create_websocket_manager(config: Config, **services) -> "WebSocketManager":
    """Create and initialize WebSocket manager"""
    manager = WebSocketManager(config, **services)
    await manager.initialize()
    return manager