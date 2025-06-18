# web/websocket.py

"""
WebSocket Manager for Real-time Features
Live price updates, trade notifications, portfolio changes
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List, Set, Any, Optional
import asyncio
import json
import logging
from datetime import datetime
import weakref

from web.auth import get_current_user
from database.models.users import User
from database.repositories import TradeRepository
from api_clients.manager import APIClientManager
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        # Active connections by user ID
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Subscriptions by user ID and topic
        self.subscriptions: Dict[str, Dict[str, Set[WebSocket]]] = {}
        # Price update tasks
        self.price_tasks: Dict[str, asyncio.Task] = {}
        # Keep track of active symbols for price updates
        self.active_symbols: Set[str] = set()
        
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
            self.subscriptions[user_id] = {}
        
        self.active_connections[user_id].add(websocket)
        
        logger.info(f"WebSocket connected for user {user_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected successfully",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Remove from all subscriptions
            for topic in self.subscriptions.get(user_id, {}):
                self.subscriptions[user_id][topic].discard(websocket)
                
                # Clean up empty subscriptions
                if not self.subscriptions[user_id][topic]:
                    del self.subscriptions[user_id][topic]
            
            # Clean up empty user entries
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if user_id in self.subscriptions:
                    del self.subscriptions[user_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
    
    async def send_user_message(self, message: Dict[str, Any], user_id: str):
        """Send message to all connections of a user"""
        if user_id in self.active_connections:
            disconnected = []
            
            for websocket in self.active_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.append(websocket)
            
            # Remove disconnected websockets
            for ws in disconnected:
                self.disconnect(ws, user_id)
    
    async def broadcast_to_subscribers(self, topic: str, message: Dict[str, Any], user_id: Optional[str] = None):
        """Broadcast message to all subscribers of a topic"""
        if user_id and user_id in self.subscriptions:
            user_subs = self.subscriptions[user_id]
            if topic in user_subs:
                disconnected = []
                
                for websocket in user_subs[topic].copy():
                    try:
                        await websocket.send_text(json.dumps(message))
                    except Exception as e:
                        logger.error(f"Error broadcasting to {topic} subscriber: {e}")
                        disconnected.append(websocket)
                
                # Remove disconnected websockets
                for ws in disconnected:
                    self.disconnect(ws, user_id)
        else:
            # Broadcast to all users
            for uid in self.subscriptions:
                await self.broadcast_to_subscribers(topic, message, uid)
    
    def subscribe(self, websocket: WebSocket, user_id: str, topic: str):
        """Subscribe WebSocket to a topic"""
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = {}
        
        if topic not in self.subscriptions[user_id]:
            self.subscriptions[user_id][topic] = set()
        
        self.subscriptions[user_id][topic].add(websocket)
        
        # Start price updates for symbol topics
        if topic.startswith("price:"):
            symbol = topic.split(":", 1)[1]
            self.active_symbols.add(symbol)
            self._ensure_price_task(symbol)
        
        logger.info(f"User {user_id} subscribed to {topic}")
    
    def unsubscribe(self, websocket: WebSocket, user_id: str, topic: str):
        """Unsubscribe WebSocket from a topic"""
        if (user_id in self.subscriptions and 
            topic in self.subscriptions[user_id]):
            
            self.subscriptions[user_id][topic].discard(websocket)
            
            if not self.subscriptions[user_id][topic]:
                del self.subscriptions[user_id][topic]
            
            # Stop price updates if no more subscribers
            if topic.startswith("price:"):
                symbol = topic.split(":", 1)[1]
                has_subscribers = any(
                    f"price:{symbol}" in user_subs 
                    for user_subs in self.subscriptions.values()
                )
                
                if not has_subscribers:
                    self.active_symbols.discard(symbol)
                    self._stop_price_task(symbol)
        
        logger.info(f"User {user_id} unsubscribed from {topic}")
    
    def _ensure_price_task(self, symbol: str):
        """Ensure price update task is running for symbol"""
        task_key = f"price_{symbol}"
        
        if task_key not in self.price_tasks or self.price_tasks[task_key].done():
            self.price_tasks[task_key] = asyncio.create_task(
                self._price_update_loop(symbol)
            )
    
    def _stop_price_task(self, symbol: str):
        """Stop price update task for symbol"""
        task_key = f"price_{symbol}"
        
        if task_key in self.price_tasks:
            self.price_tasks[task_key].cancel()
            del self.price_tasks[task_key]
    
    async def _price_update_loop(self, symbol: str):
        """Price update loop for a symbol"""
        api_manager = APIClientManager()
        
        try:
            while symbol in self.active_symbols:
                try:
                    # Get ticker data
                    ticker = await api_manager.ccxt_client.get_ticker(symbol)
                    
                    if ticker:
                        price_message = {
                            "type": "price_update",
                            "symbol": symbol,
                            "price": ticker.get("last", 0),
                            "change_24h": ticker.get("percentage", 0),
                            "volume_24h": ticker.get("quoteVolume", 0),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        await self.broadcast_to_subscribers(f"price:{symbol}", price_message)
                    
                    # Update every 5 seconds
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Price update error for {symbol}: {e}")
                    await asyncio.sleep(10)  # Wait longer on error
                    
        except asyncio.CancelledError:
            logger.info(f"Price update task cancelled for {symbol}")
        except Exception as e:
            logger.error(f"Price update loop error for {symbol}: {e}")

# Global connection manager
manager = ConnectionManager()

# WebSocket router
router = APIRouter()

@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint"""
    user_id = None
    
    try:
        # Get user from query parameters (for WebSocket, we use token)
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        # Verify token and get user
        from web.auth import auth_manager
        user = await auth_manager.get_user_by_token(token)
        
        if not user:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        user_id = str(user.id)
        
        # Connect user
        await manager.connect(websocket, user_id)
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            await handle_websocket_message(websocket, user_id, message)
            
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if user_id:
            manager.disconnect(websocket, user_id)

async def handle_websocket_message(websocket: WebSocket, user_id: str, message: Dict[str, Any]):
    """Handle incoming WebSocket messages"""
    
    message_type = message.get("type")
    
    try:
        if message_type == "subscribe":
            # Subscribe to topic
            topic = message.get("topic")
            if topic:
                manager.subscribe(websocket, user_id, topic)
                
                await manager.send_personal_message({
                    "type": "subscription",
                    "topic": topic,
                    "status": "subscribed",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
        
        elif message_type == "unsubscribe":
            # Unsubscribe from topic
            topic = message.get("topic")
            if topic:
                manager.unsubscribe(websocket, user_id, topic)
                
                await manager.send_personal_message({
                    "type": "subscription",
                    "topic": topic,
                    "status": "unsubscribed",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
        
        elif message_type == "ping":
            # Respond to ping
            await manager.send_personal_message({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        elif message_type == "get_portfolio":
            # Send current portfolio data
            portfolio_data = await get_portfolio_data(user_id)
            
            await manager.send_personal_message({
                "type": "portfolio_update",
                "data": portfolio_data,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        elif message_type == "get_active_trades":
            # Send active trades
            trades_data = await get_active_trades_data(user_id)
            
            await manager.send_personal_message({
                "type": "trades_update",
                "data": trades_data,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        else:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

# Helper functions for real-time data
async def get_portfolio_data(user_id: str) -> Dict[str, Any]:
    """Get current portfolio data"""
    try:
        # This would integrate with your existing dashboard data function
        from web.routes.dashboard import calculate_portfolio_metrics
        from database.repositories import TradeRepository, ExchangeRepository
        
        trade_repo = TradeRepository()
        exchange_repo = ExchangeRepository()
        
        active_trades = await trade_repo.get_active_trades(user_id)
        recent_trades = await trade_repo.get_recent_trades(user_id, limit=10)
        exchanges = await exchange_repo.get_user_exchanges(user_id)
        
        metrics = await calculate_portfolio_metrics(
            user_id, active_trades, recent_trades, exchanges
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting portfolio data: {e}")
        return {}

async def get_active_trades_data(user_id: str) -> List[Dict[str, Any]]:
    """Get active trades data"""
    try:
        from database.repositories import TradeRepository
        from web.routes.dashboard import format_trade_for_display
        
        trade_repo = TradeRepository()
        active_trades = await trade_repo.get_active_trades(user_id)
        
        return [format_trade_for_display(trade) for trade in active_trades]
        
    except Exception as e:
        logger.error(f"Error getting active trades: {e}")
        return []

# Notification functions for external use
async def notify_trade_execution(user_id: str, trade_data: Dict[str, Any]):
    """Notify user of trade execution"""
    message = {
        "type": "trade_executed",
        "data": trade_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.send_user_message(message, user_id)

async def notify_strategy_signal(user_id: str, signal_data: Dict[str, Any]):
    """Notify user of strategy signal"""
    message = {
        "type": "strategy_signal",
        "data": signal_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.send_user_message(message, user_id)

async def notify_portfolio_update(user_id: str, portfolio_data: Dict[str, Any]):
    """Notify user of portfolio changes"""
    message = {
        "type": "portfolio_update",
        "data": portfolio_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.send_user_message(message, user_id)

async def notify_backtest_complete(user_id: str, backtest_data: Dict[str, Any]):
    """Notify user of backtest completion"""
    message = {
        "type": "backtest_complete",
        "data": backtest_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.send_user_message(message, user_id)

async def notify_system_alert(user_id: str, alert_data: Dict[str, Any]):
    """Notify user of system alerts"""
    message = {
        "type": "system_alert",
        "data": alert_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.send_user_message(message, user_id)

# Cleanup function
async def cleanup_websocket_manager():
    """Cleanup WebSocket manager resources"""
    # Cancel all price tasks
    for task in manager.price_tasks.values():
        task.cancel()
    
    # Wait for tasks to complete
    if manager.price_tasks:
        await asyncio.gather(*manager.price_tasks.values(), return_exceptions=True)
    
    manager.price_tasks.clear()
    manager.active_symbols.clear()
    logger.info("WebSocket manager cleaned up")
