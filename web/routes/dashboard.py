# web/routes/dashboard.py

"""
Dashboard Routes
Main dashboard with portfolio overview, active trades, and performance metrics
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from web.auth import require_auth
from database.models.users import User
from database.repositories import (
    TradeRepository, StrategyRepository, BacktestRepository,
    ExchangeRepository, NotificationRepository
)
from api_clients.manager import APIClientManager
from core.trading_engine import TradingEngine
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

# Repositories
trade_repo = TradeRepository()
strategy_repo = StrategyRepository()
backtest_repo = BacktestRepository()
exchange_repo = ExchangeRepository()
notification_repo = NotificationRepository()

# Services
config = ConfigManager()
api_manager = APIClientManager()

@router.get("/dashboard")
async def dashboard(
    request: Request,
    user: User = Depends(require_auth),
    timeframe: str = Query("24h", description="Timeframe for data")
):
    """Main dashboard page"""
    try:
        # Get dashboard data
        dashboard_data = await get_dashboard_data(user.id, timeframe)
        
        return templates.TemplateResponse("dashboard/index.html", {
            "request": request,
            "user": user,
            "dashboard_data": dashboard_data,
            "timeframe": timeframe,
            "page_title": "Dashboard"
        })
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")

@router.get("/api/dashboard-data")
async def api_dashboard_data(
    user: User = Depends(require_auth),
    timeframe: str = Query("24h")
):
    """API endpoint for dashboard data"""
    try:
        data = await get_dashboard_data(user.id, timeframe)
        return JSONResponse(content=data)
        
    except Exception as e:
        logger.error(f"Dashboard API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")

async def get_dashboard_data(user_id: str, timeframe: str) -> Dict[str, Any]:
    """Get comprehensive dashboard data"""
    
    # Parse timeframe
    timeframe_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    
    time_delta = timeframe_map.get(timeframe, timedelta(days=1))
    start_time = datetime.utcnow() - time_delta
    
    # Get active trades
    active_trades = await trade_repo.get_active_trades(user_id)
    
    # Get recent trades
    recent_trades = await trade_repo.get_trades_by_timeframe(
        user_id, start_time, datetime.utcnow()
    )
    
    # Get active strategies
    active_strategies = await strategy_repo.get_active_strategies(user_id)
    
    # Get user exchanges
    user_exchanges = await exchange_repo.get_user_exchanges(user_id)
    
    # Calculate portfolio metrics
    portfolio_metrics = await calculate_portfolio_metrics(
        user_id, active_trades, recent_trades, user_exchanges
    )
    
    # Get recent notifications
    recent_notifications = await notification_repo.get_recent_notifications(
        user_id, limit=10
    )
    
    # Get performance data
    performance_data = await get_performance_data(user_id, timeframe)
    
    # Get market overview
    market_overview = await get_market_overview()
    
    return {
        "portfolio_metrics": portfolio_metrics,
        "active_trades": [format_trade_for_display(trade) for trade in active_trades],
        "recent_trades": [format_trade_for_display(trade) for trade in recent_trades[-10:]],
        "active_strategies": [format_strategy_for_display(strategy) for strategy in active_strategies],
        "exchanges": [format_exchange_for_display(exchange) for exchange in user_exchanges],
        "notifications": [format_notification_for_display(notif) for notif in recent_notifications],
        "performance": performance_data,
        "market_overview": market_overview,
        "timeframe": timeframe,
        "last_updated": datetime.utcnow().isoformat()
    }

async def calculate_portfolio_metrics(
    user_id: str,
    active_trades: List,
    recent_trades: List,
    exchanges: List
) -> Dict[str, Any]:
    """Calculate portfolio performance metrics"""
    
    # Get total balances from exchanges
    total_balance = 0.0
    available_balance = 0.0
    
    for exchange in exchanges:
        try:
            if exchange.active:
                balance_data = await api_manager.ccxt_client.get_balance(
                    exchange.exchange_name,
                    exchange.api_key_encrypted,
                    exchange.api_secret_encrypted
                )
                
                # Sum USDT balances (or configured base currency)
                base_currency = config.get("trading.default_quote_currency", "USDT")
                if base_currency in balance_data.get("total", {}):
                    total_balance += balance_data["total"][base_currency]
                if base_currency in balance_data.get("free", {}):
                    available_balance += balance_data["free"][base_currency]
                    
        except Exception as e:
            logger.warning(f"Failed to get balance for exchange {exchange.exchange_name}: {e}")
    
    # Calculate active positions value
    active_positions_value = 0.0
    active_positions_count = len(active_trades)
    
    for trade in active_trades:
        active_positions_value += trade.amount * trade.price
    
    # Calculate PnL from recent trades
    total_pnl = 0.0
    winning_trades = 0
    losing_trades = 0
    total_trades = len(recent_trades)
    
    for trade in recent_trades:
        if trade.status == "filled" and hasattr(trade, "pnl"):
            total_pnl += trade.pnl or 0.0
            if (trade.pnl or 0.0) > 0:
                winning_trades += 1
            else:
                losing_trades += 1
    
    # Calculate win rate
    win_rate = (winning_trades / max(total_trades, 1)) * 100
    
    # Calculate daily change (simplified)
    daily_change = 0.0
    daily_change_pct = 0.0
    
    if total_trades > 0:
        daily_change = total_pnl
        daily_change_pct = (daily_change / max(total_balance - daily_change, 1)) * 100
    
    return {
        "total_balance": round(total_balance, 2),
        "available_balance": round(available_balance, 2),
        "active_positions_value": round(active_positions_value, 2),
        "active_positions_count": active_positions_count,
        "total_pnl": round(total_pnl, 2),
        "daily_change": round(daily_change, 2),
        "daily_change_pct": round(daily_change_pct, 2),
        "win_rate": round(win_rate, 1),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades
    }

async def get_performance_data(user_id: str, timeframe: str) -> Dict[str, Any]:
    """Get performance chart data"""
    
    # Parse timeframe for data points
    if timeframe == "1h":
        intervals = 12  # 5-minute intervals
        interval_duration = timedelta(minutes=5)
    elif timeframe == "6h":
        intervals = 24  # 15-minute intervals  
        interval_duration = timedelta(minutes=15)
    elif timeframe == "24h":
        intervals = 24  # 1-hour intervals
        interval_duration = timedelta(hours=1)
    elif timeframe == "7d":
        intervals = 7  # 1-day intervals
        interval_duration = timedelta(days=1)
    else:  # 30d
        intervals = 30  # 1-day intervals
        interval_duration = timedelta(days=1)
    
    end_time = datetime.utcnow()
    start_time = end_time - (interval_duration * intervals)
    
    # Get trades in timeframe
    trades = await trade_repo.get_trades_by_timeframe(user_id, start_time, end_time)
    
    # Calculate cumulative PnL over time
    performance_points = []
    cumulative_pnl = 0.0
    
    for i in range(intervals):
        point_time = start_time + (interval_duration * i)
        
        # Find trades in this interval
        interval_pnl = 0.0
        for trade in trades:
            if (trade.execution_time and 
                point_time <= trade.execution_time < point_time + interval_duration and
                trade.status == "filled"):
                interval_pnl += trade.pnl or 0.0
        
        cumulative_pnl += interval_pnl
        
        performance_points.append({
            "time": point_time.isoformat(),
            "pnl": round(cumulative_pnl, 2),
            "trades": len([t for t in trades if t.execution_time and 
                          point_time <= t.execution_time < point_time + interval_duration])
        })
    
    return {
        "chart_data": performance_points,
        "total_return": round(cumulative_pnl, 2),
        "best_day": round(max([p["pnl"] for p in performance_points] + [0]), 2),
        "worst_day": round(min([p["pnl"] for p in performance_points] + [0]), 2)
    }

async def get_market_overview() -> Dict[str, Any]:
    """Get general market overview data"""
    
    try:
        # Get major crypto prices
        major_pairs = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
        market_data = []
        
        for symbol in major_pairs:
            try:
                ticker = await api_manager.ccxt_client.get_ticker(symbol)
                market_data.append({
                    "symbol": symbol,
                    "price": ticker.get("last", 0),
                    "change_24h": ticker.get("percentage", 0),
                    "volume_24h": ticker.get("quoteVolume", 0)
                })
            except Exception as e:
                logger.warning(f"Failed to get ticker for {symbol}: {e}")
        
        return {
            "major_pairs": market_data,
            "market_sentiment": "neutral",  # Could be enhanced with sentiment analysis
            "volatility_index": 0.0  # Could be calculated from price data
        }
        
    except Exception as e:
        logger.error(f"Market overview error: {e}")
        return {
            "major_pairs": [],
            "market_sentiment": "unknown",
            "volatility_index": 0.0
        }

def format_trade_for_display(trade) -> Dict[str, Any]:
    """Format trade data for display"""
    return {
        "id": str(trade.id),
        "symbol": trade.symbol,
        "side": trade.side,
        "type": trade.type,
        "amount": trade.amount,
        "price": trade.price,
        "filled_amount": trade.filled_amount or 0,
        "status": trade.status,
        "pnl": getattr(trade, "pnl", 0) or 0,
        "timestamp": trade.timestamp.isoformat() if trade.timestamp else None,
        "execution_time": trade.execution_time.isoformat() if trade.execution_time else None
    }

def format_strategy_for_display(strategy) -> Dict[str, Any]:
    """Format strategy data for display"""
    return {
        "id": str(strategy.id),
        "name": strategy.name,
        "type": strategy.strategy_type,
        "active": strategy.active,
        "description": strategy.description[:100] + "..." if len(strategy.description) > 100 else strategy.description
    }

def format_exchange_for_display(exchange) -> Dict[str, Any]:
    """Format exchange data for display"""
    return {
        "id": str(exchange.id),
        "name": exchange.exchange_name,
        "display_name": exchange.display_name,
        "active": exchange.active,
        "testnet": exchange.testnet
    }

def format_notification_for_display(notification) -> Dict[str, Any]:
    """Format notification data for display"""
    return {
        "id": str(notification.id),
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "timestamp": notification.sent_at.isoformat() if notification.sent_at else None,
        "read": notification.read
    }
