# web/routes/api.py

"""
API Routes
RESTful API endpoints for external integrations and AJAX requests
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import logging

from web.auth import require_auth, verify_token
from database.models.users import User
from database.repositories import (
    TradeRepository, StrategyRepository, BacktestRepository,
    ExchangeRepository, NotificationRepository
)
from api_clients.manager import APIClientManager
from core.trading_engine import TradingEngine
from core.risk_manager import RiskManager
from strategies.manager import StrategyManager
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Services
trade_repo = TradeRepository()
strategy_repo = StrategyRepository()
backtest_repo = BacktestRepository()
exchange_repo = ExchangeRepository()
notification_repo = NotificationRepository()
api_manager = APIClientManager()
trading_engine = TradingEngine()
risk_manager = RiskManager()
strategy_manager = StrategyManager()
config = ConfigManager()

# Pydantic models for API requests
class TradeOrderRequest(BaseModel):
    exchange: str
    symbol: str
    side: str  # buy/sell
    type: str  # market/limit
    amount: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class StrategyActivateRequest(BaseModel):
    strategy_id: str
    active: bool

class BacktestRunRequest(BaseModel):
    strategy_id: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_balance: float = 10000.0

# Market Data Endpoints
@router.get("/market/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    exchange: Optional[str] = Query(None)
):
    """Get ticker data for symbol"""
    try:
        ticker = await api_manager.ccxt_client.get_ticker(symbol, exchange)
        return JSONResponse(content=ticker)
        
    except Exception as e:
        logger.error(f"Get ticker error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ticker data")

@router.get("/market/ohlcv/{symbol}")
async def get_ohlcv(
    symbol: str,
    timeframe: str = Query("1h"),
    limit: int = Query(100, ge=1, le=1000),
    exchange: Optional[str] = Query(None)
):
    """Get OHLCV candlestick data"""
    try:
        data = await api_manager.ccxt_client.get_market_data(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            exchange=exchange
        )
        return JSONResponse(content=data)
        
    except Exception as e:
        logger.error(f"Get OHLCV error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get OHLCV data")

@router.get("/market/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    limit: int = Query(50, ge=5, le=100),
    exchange: Optional[str] = Query(None)
):
    """Get orderbook data"""
    try:
        orderbook = await api_manager.ccxt_client.get_orderbook(symbol, exchange, limit)
        return JSONResponse(content=orderbook)
        
    except Exception as e:
        logger.error(f"Get orderbook error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get orderbook data")

# Trading Endpoints
@router.get("/trading/balance")
async def get_balance(
    exchange: str,
    user: User = Depends(require_auth)
):
    """Get account balance"""
    try:
        user_exchange = await exchange_repo.get_user_exchange(user.id, exchange)
        if not user_exchange:
            raise HTTPException(status_code=400, detail="Exchange not configured")
        
        balance = await api_manager.ccxt_client.get_balance(
            exchange,
            user_exchange.api_key_encrypted,
            user_exchange.api_secret_encrypted
        )
        
        return JSONResponse(content=balance)
        
    except Exception as e:
        logger.error(f"Get balance error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get balance")

@router.post("/trading/order")
async def place_order(
    order: TradeOrderRequest,
    user: User = Depends(require_auth)
):
    """Place trading order"""
    try:
        # Verify exchange configuration
        user_exchange = await exchange_repo.get_user_exchange(user.id, order.exchange)
        if not user_exchange:
            raise HTTPException(status_code=400, detail="Exchange not configured")
        
        # Risk validation
        risk_check = await risk_manager.validate_trade(
            user_id=str(user.id),
            symbol=order.symbol,
            side=order.side,
            amount=order.amount,
            price=order.price or 0,
            exchange=order.exchange
        )
        
        if not risk_check["allowed"]:
            raise HTTPException(status_code=400, detail=risk_check["reason"])
        
        # Place order
        result = await trading_engine.place_order(
            user_id=str(user.id),
            exchange=order.exchange,
            symbol=order.symbol,
            side=order.side,
            order_type=order.type,
            amount=order.amount,
            price=order.price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Place order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to place order")

@router.delete("/trading/order/{order_id}")
async def cancel_order(
    order_id: str,
    exchange: str,
    user: User = Depends(require_auth)
):
    """Cancel trading order"""
    try:
        # Verify order belongs to user
        trade = await trade_repo.get_trade_by_order_id(order_id)
        if not trade or str(trade.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Cancel order
        result = await trading_engine.cancel_order(
            user_id=str(user.id),
            order_id=order_id,
            exchange=exchange
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Cancel order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel order")

@router.get("/trading/orders")
async def get_orders(
    user: User = Depends(require_auth),
    status: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get user orders"""
    try:
        filters = {"limit": limit}
        if status:
            filters["status"] = status
        if exchange:
            filters["exchange"] = exchange
        
        orders = await trade_repo.get_user_trades(user.id, filters)
        
        return JSONResponse(content=[
            {
                "id": str(order.id),
                "order_id": order.order_id,
                "exchange": order.exchange,
                "symbol": order.symbol,
                "side": order.side,
                "type": order.type,
                "amount": order.amount,
                "price": order.price,
                "filled_amount": order.filled_amount or 0,
                "status": order.status,
                "timestamp": order.timestamp.isoformat() if order.timestamp else None,
                "execution_time": order.execution_time.isoformat() if order.execution_time else None
            }
            for order in orders
        ])
        
    except Exception as e:
        logger.error(f"Get orders error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get orders")

# Strategy Endpoints
@router.get("/strategies")
async def get_strategies(
    user: User = Depends(require_auth),
    active_only: bool = Query(False)
):
    """Get user strategies"""
    try:
        if active_only:
            strategies = await strategy_repo.get_active_strategies(user.id)
        else:
            strategies = await strategy_repo.get_user_strategies(user.id)
        
        return JSONResponse(content=[
            {
                "id": str(strategy.id),
                "name": strategy.name,
                "description": strategy.description,
                "strategy_type": strategy.strategy_type,
                "active": strategy.active,
                "public": strategy.public,
                "config": strategy.config,
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                "updated_at": strategy.updated_at.isoformat() if strategy.updated_at else None
            }
            for strategy in strategies
        ])
        
    except Exception as e:
        logger.error(f"Get strategies error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get strategies")

@router.post("/strategies/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    request: StrategyActivateRequest,
    user: User = Depends(require_auth)
):
    """Activate/deactivate strategy"""
    try:
        # Verify strategy belongs to user
        strategy = await strategy_repo.get_by_id(strategy_id)
        if not strategy or str(strategy.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Update strategy status
        await strategy_repo.update(strategy_id, {"active": request.active})
        
        # Update strategy manager
        if request.active:
            await strategy_manager.activate_strategy(strategy_id)
        else:
            await strategy_manager.deactivate_strategy(strategy_id)
        
        return JSONResponse(content={
            "success": True,
            "strategy_id": strategy_id,
            "active": request.active,
            "message": f"Strategy {'activated' if request.active else 'deactivated'}"
        })
        
    except Exception as e:
        logger.error(f"Activate strategy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update strategy")

# Backtesting Endpoints
@router.post("/backtesting/run")
async def run_backtest_api(
    request: BacktestRunRequest,
    user: User = Depends(require_auth)
):
    """Run backtest via API"""
    try:
        # Verify strategy belongs to user
        strategy = await strategy_repo.get_by_id(request.strategy_id)
        if not strategy or str(strategy.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Parse dates
        try:
            start_dt = datetime.fromisoformat(request.start_date)
            end_dt = datetime.fromisoformat(request.end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
        
        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        # Create backtest record
        backtest = await backtest_repo.create({
            "user_id": user.id,
            "strategy_id": request.strategy_id,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "start_date": start_dt,
            "end_date": end_dt,
            "initial_balance": request.initial_balance,
            "status": "queued"
        })
        
        return JSONResponse(content={
            "success": True,
            "backtest_id": str(backtest.id),
            "status": "queued",
            "message": "Backtest queued for execution"
        })
        
    except Exception as e:
        logger.error(f"Run backtest API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start backtest")

@router.get("/backtesting/results")
async def get_backtest_results(
    user: User = Depends(require_auth),
    strategy_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get backtest results"""
    try:
        filters = {"limit": limit}
        if strategy_id:
            filters["strategy_id"] = strategy_id
        
        backtests = await backtest_repo.get_user_backtests(user.id, filters)
        
        return JSONResponse(content=[
            {
                "id": str(backtest.id),
                "strategy_id": str(backtest.strategy_id),
                "symbol": backtest.symbol,
                "timeframe": backtest.timeframe,
                "start_date": backtest.start_date.isoformat(),
                "end_date": backtest.end_date.isoformat(),
                "initial_balance": backtest.initial_balance,
                "final_balance": backtest.final_balance,
                "total_trades": backtest.total_trades,
                "winning_trades": backtest.winning_trades,
                "losing_trades": backtest.losing_trades,
                "results": backtest.results,
                "status": getattr(backtest, "status", "completed"),
                "created_at": backtest.created_at.isoformat() if backtest.created_at else None
            }
            for backtest in backtests
        ])
        
    except Exception as e:
        logger.error(f"Get backtest results error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get backtest results")

# Portfolio Endpoints
@router.get("/portfolio/overview")
async def get_portfolio_overview(
    user: User = Depends(require_auth),
    timeframe: str = Query("24h")
):
    """Get portfolio overview"""
    try:
        from web.routes.dashboard import get_dashboard_data
        
        dashboard_data = await get_dashboard_data(user.id, timeframe)
        
        return JSONResponse(content={
            "portfolio_metrics": dashboard_data.get("portfolio_metrics", {}),
            "performance": dashboard_data.get("performance", {}),
            "active_trades_count": len(dashboard_data.get("active_trades", [])),
            "timeframe": timeframe,
            "last_updated": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Get portfolio overview error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get portfolio overview")

@router.get("/portfolio/performance")
async def get_portfolio_performance(
    user: User = Depends(require_auth),
    days: int = Query(30, ge=1, le=365)
):
    """Get portfolio performance data"""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get trades in timeframe
        trades = await trade_repo.get_trades_by_timeframe(user.id, start_date, end_date)
        
        # Calculate performance metrics
        performance_data = calculate_performance_data(trades, days)
        
        return JSONResponse(content=performance_data)
        
    except Exception as e:
        logger.error(f"Get portfolio performance error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance data")

# Chart Endpoints
@router.get("/charts/price/{symbol}")
async def get_price_chart(
    symbol: str,
    timeframe: str = Query("1h"),
    limit: int = Query(100, ge=1, le=1000),
    indicators: Optional[str] = Query(None)
):
    """Get price chart with optional indicators"""
    try:
        # Get market data
        market_data = await api_manager.ccxt_client.get_market_data(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit
        )
        
        chart_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": market_data
        }
        
        # Add indicators if requested
        if indicators:
            indicator_list = [i.strip() for i in indicators.split(',')]
            chart_data["indicators"] = {}
            
            for indicator in indicator_list:
                if indicator.upper() == "RSI":
                    rsi_data = await api_manager.ccxt_client.get_rsi(symbol, period=14)
                    chart_data["indicators"]["rsi"] = rsi_data
        
        return JSONResponse(content=chart_data)
        
    except Exception as e:
        logger.error(f"Get price chart error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chart data")

@router.post("/charts/generate")
async def generate_chart(
    request: Request,
    chart_config: Dict[str, Any],
    user: User = Depends(require_auth)
):
    """Generate chart using QuickChart"""
    try:
        chart_url = await api_manager.quickchart_client.generate_chart(chart_config)
        
        return JSONResponse(content={
            "success": True,
            "chart_url": chart_url,
            "config": chart_config
        })
        
    except Exception as e:
        logger.error(f"Generate chart error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate chart")

# Notification Endpoints
@router.get("/notifications")
async def get_notifications(
    user: User = Depends(require_auth),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get user notifications"""
    try:
        filters = {"limit": limit}
        if unread_only:
            filters["read"] = False
        
        notifications = await notification_repo.get_user_notifications(user.id, filters)
        
        return JSONResponse(content=[
            {
                "id": str(notif.id),
                "type": notif.type,
                "title": notif.title,
                "message": notif.message,
                "read": notif.read,
                "timestamp": notif.sent_at.isoformat() if notif.sent_at else None,
                "metadata": notif.metadata
            }
            for notif in notifications
        ])
        
    except Exception as e:
        logger.error(f"Get notifications error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notifications")

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: User = Depends(require_auth)
):
    """Mark notification as read"""
    try:
        # Verify notification belongs to user
        notification = await notification_repo.get_by_id(notification_id)
        if not notification or str(notification.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Notification not found")
        
        # Mark as read
        await notification_repo.mark_as_read(notification_id)
        
        return JSONResponse(content={
            "success": True,
            "notification_id": notification_id,
            "message": "Notification marked as read"
        })
        
    except Exception as e:
        logger.error(f"Mark notification read error: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")

# System Status Endpoints
@router.get("/system/status")
async def get_system_status():
    """Get system status"""
    try:
        # Check various system components
        status = {
            "api": "healthy",
            "database": "healthy",
            "ccxt_gateway": "checking",
            "quickchart": "checking",
            "trading_engine": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Test external services
        try:
            await api_manager.ccxt_client.get_ticker("BTC/USDT")
            status["ccxt_gateway"] = "healthy"
        except Exception:
            status["ccxt_gateway"] = "error"
        
        try:
            test_chart = {"chart": {"type": "line", "data": {"datasets": []}}}
            await api_manager.quickchart_client.generate_chart(test_chart)
            status["quickchart"] = "healthy"
        except Exception:
            status["quickchart"] = "error"
        
        return JSONResponse(content=status)
        
    except Exception as e:
        logger.error(f"Get system status error: {e}")
        return JSONResponse(content={
            "api": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=500)

# Helper functions
def calculate_performance_data(trades: List, days: int) -> Dict[str, Any]:
    """Calculate performance data from trades"""
    
    if not trades:
        return {
            "total_pnl": 0.0,
            "total_trades": 0,
            "win_rate": 0.0,
            "daily_pnl": [],
            "cumulative_pnl": []
        }
    
    # Calculate basic metrics
    total_pnl = sum(trade.pnl or 0 for trade in trades if hasattr(trade, 'pnl'))
    total_trades = len(trades)
    winning_trades = sum(1 for trade in trades if hasattr(trade, 'pnl') and (trade.pnl or 0) > 0)
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    # Calculate daily PnL
    daily_pnl = {}
    for trade in trades:
        if hasattr(trade, 'execution_time') and trade.execution_time:
            date_key = trade.execution_time.date().isoformat()
            if date_key not in daily_pnl:
                daily_pnl[date_key] = 0
            daily_pnl[date_key] += trade.pnl or 0
    
    # Calculate cumulative PnL
    cumulative_pnl = []
    running_total = 0
    
    for date in sorted(daily_pnl.keys()):
        running_total += daily_pnl[date]
        cumulative_pnl.append({
            "date": date,
            "pnl": round(running_total, 2)
        })
    
    return {
        "total_pnl": round(total_pnl, 2),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "win_rate": round(win_rate, 2),
        "daily_pnl": [{"date": date, "pnl": round(pnl, 2)} for date, pnl in daily_pnl.items()],
        "cumulative_pnl": cumulative_pnl
    }
