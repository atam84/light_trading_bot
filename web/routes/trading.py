# web/routes/trading.py

"""
Trading Routes
Manual trading interface, order management, and trade history
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from web.auth import require_auth, generate_csrf_token
from database.models.users import User
from database.repositories import TradeRepository, ExchangeRepository
from api_clients.manager import APIClientManager
from core.trading_engine import TradingEngine
from core.risk_manager import RiskManager
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

# Repositories and services
trade_repo = TradeRepository()
exchange_repo = ExchangeRepository()
api_manager = APIClientManager()
risk_manager = RiskManager()
config = ConfigManager()

# Pydantic models
class TradeRequest(BaseModel):
    exchange: str
    symbol: str
    side: str  # buy/sell
    type: str  # market/limit
    amount: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    @validator('side')
    def validate_side(cls, v):
        if v not in ['buy', 'sell']:
            raise ValueError('Side must be "buy" or "sell"')
        return v
    
    @validator('type')
    def validate_type(cls, v):
        if v not in ['market', 'limit']:
            raise ValueError('Type must be "market" or "limit"')
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

class CancelOrderRequest(BaseModel):
    order_id: str
    exchange: str

@router.get("/")
async def trading_page(
    request: Request,
    user: User = Depends(require_auth)
):
    """Main trading interface"""
    try:
        # Get user exchanges
        exchanges = await exchange_repo.get_user_exchanges(user.id)
        
        # Get active trades
        active_trades = await trade_repo.get_active_trades(user.id)
        
        # Get recent trades
        recent_trades = await trade_repo.get_recent_trades(user.id, limit=50)
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("trading/index.html", {
            "request": request,
            "user": user,
            "exchanges": exchanges,
            "active_trades": active_trades,
            "recent_trades": recent_trades,
            "csrf_token": csrf_token,
            "page_title": "Trading"
        })
        
    except Exception as e:
        logger.error(f"Trading page error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load trading page")

@router.get("/orders")
async def orders_page(
    request: Request,
    user: User = Depends(require_auth),
    status: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None)
):
    """Orders management page"""
    try:
        # Get filters
        filters = {}
        if status:
            filters["status"] = status
        if exchange:
            filters["exchange"] = exchange
        
        # Get orders
        orders = await trade_repo.get_user_trades(user.id, filters)
        
        # Get exchanges for filter dropdown
        exchanges = await exchange_repo.get_user_exchanges(user.id)
        
        return templates.TemplateResponse("trading/orders.html", {
            "request": request,
            "user": user,
            "orders": orders,
            "exchanges": exchanges,
            "current_status": status,
            "current_exchange": exchange,
            "page_title": "Orders"
        })
        
    except Exception as e:
        logger.error(f"Orders page error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load orders")

@router.get("/history")
async def history_page(
    request: Request,
    user: User = Depends(require_auth),
    days: int = Query(7, ge=1, le=365),
    symbol: Optional[str] = Query(None)
):
    """Trade history page"""
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get trade history
        trades = await trade_repo.get_trades_by_timeframe(
            user.id, start_date, end_date, symbol
        )
        
        # Calculate statistics
        stats = calculate_trade_stats(trades)
        
        return templates.TemplateResponse("trading/history.html", {
            "request": request,
            "user": user,
            "trades": trades,
            "stats": stats,
            "days": days,
            "symbol": symbol,
            "page_title": "Trade History"
        })
        
    except Exception as e:
        logger.error(f"History page error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load history")

@router.post("/place-order")
async def place_order(
    request: Request,
    exchange: str = Form(...),
    symbol: str = Form(...),
    side: str = Form(...),
    order_type: str = Form(...),
    amount: float = Form(...),
    price: Optional[float] = Form(None),
    stop_loss: Optional[float] = Form(None),
    take_profit: Optional[float] = Form(None),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Place a new order"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Validate inputs
        trade_request = TradeRequest(
            exchange=exchange,
            symbol=symbol,
            side=side,
            type=order_type,
            amount=amount,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # Get exchange configuration
        user_exchange = await exchange_repo.get_user_exchange(user.id, exchange)
        if not user_exchange:
            raise HTTPException(status_code=400, detail="Exchange not configured")
        
        # Risk validation
        risk_check = await risk_manager.validate_trade(
            user_id=str(user.id),
            symbol=symbol,
            side=side,
            amount=amount,
            price=price or 0,
            exchange=exchange
        )
        
        if not risk_check["allowed"]:
            raise HTTPException(status_code=400, detail=risk_check["reason"])
        
        # Place order via trading engine
        trading_engine = TradingEngine()
        
        order_result = await trading_engine.place_order(
            user_id=str(user.id),
            exchange=exchange,
            symbol=symbol,
            side=side,
            order_type=order_type,
            amount=amount,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        if order_result["success"]:
            # Redirect back to trading page with success message
            return RedirectResponse(
                url="/trading?success=Order placed successfully",
                status_code=302
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=order_result.get("error", "Failed to place order")
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Place order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to place order")

@router.post("/cancel-order")
async def cancel_order(
    request: Request,
    order_id: str = Form(...),
    exchange: str = Form(...),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Cancel an existing order"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Verify order belongs to user
        trade = await trade_repo.get_trade_by_order_id(order_id)
        if not trade or str(trade.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Cancel order via trading engine
        trading_engine = TradingEngine()
        
        cancel_result = await trading_engine.cancel_order(
            user_id=str(user.id),
            order_id=order_id,
            exchange=exchange
        )
        
        if cancel_result["success"]:
            return RedirectResponse(
                url="/trading/orders?success=Order cancelled successfully",
                status_code=302
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=cancel_result.get("error", "Failed to cancel order")
            )
        
    except Exception as e:
        logger.error(f"Cancel order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel order")

# API endpoints for AJAX requests
@router.get("/api/balance")
async def api_get_balance(
    exchange: str,
    user: User = Depends(require_auth)
):
    """Get account balance for exchange"""
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

@router.get("/api/ticker")
async def api_get_ticker(
    symbol: str,
    exchange: Optional[str] = None
):
    """Get ticker data for symbol"""
    try:
        ticker = await api_manager.ccxt_client.get_ticker(symbol, exchange)
        return JSONResponse(content=ticker)
        
    except Exception as e:
        logger.error(f"Get ticker error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ticker")

@router.get("/api/orderbook")
async def api_get_orderbook(
    symbol: str,
    exchange: Optional[str] = None,
    limit: int = Query(20, ge=5, le=100)
):
    """Get orderbook data for symbol"""
    try:
        orderbook = await api_manager.ccxt_client.get_orderbook(symbol, exchange, limit)
        return JSONResponse(content=orderbook)
        
    except Exception as e:
        logger.error(f"Get orderbook error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get orderbook")

@router.get("/api/trades")
async def api_get_trades(
    user: User = Depends(require_auth),
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000)
):
    """Get user trades via API"""
    try:
        filters = {"limit": limit}
        if status:
            filters["status"] = status
        
        trades = await trade_repo.get_user_trades(user.id, filters)
        
        return JSONResponse(content=[
            {
                "id": str(trade.id),
                "symbol": trade.symbol,
                "side": trade.side,
                "type": trade.type,
                "amount": trade.amount,
                "price": trade.price,
                "filled_amount": trade.filled_amount or 0,
                "status": trade.status,
                "timestamp": trade.timestamp.isoformat() if trade.timestamp else None,
                "execution_time": trade.execution_time.isoformat() if trade.execution_time else None
            }
            for trade in trades
        ])
        
    except Exception as e:
        logger.error(f"Get trades API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trades")

@router.post("/api/place-order")
async def api_place_order(
    trade_request: TradeRequest,
    user: User = Depends(require_auth)
):
    """Place order via API"""
    try:
        # Get exchange configuration
        user_exchange = await exchange_repo.get_user_exchange(user.id, trade_request.exchange)
        if not user_exchange:
            raise HTTPException(status_code=400, detail="Exchange not configured")
        
        # Risk validation
        risk_check = await risk_manager.validate_trade(
            user_id=str(user.id),
            symbol=trade_request.symbol,
            side=trade_request.side,
            amount=trade_request.amount,
            price=trade_request.price or 0,
            exchange=trade_request.exchange
        )
        
        if not risk_check["allowed"]:
            raise HTTPException(status_code=400, detail=risk_check["reason"])
        
        # Place order
        trading_engine = TradingEngine()
        
        result = await trading_engine.place_order(
            user_id=str(user.id),
            exchange=trade_request.exchange,
            symbol=trade_request.symbol,
            side=trade_request.side,
            order_type=trade_request.type,
            amount=trade_request.amount,
            price=trade_request.price,
            stop_loss=trade_request.stop_loss,
            take_profit=trade_request.take_profit
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"API place order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to place order")

def calculate_trade_stats(trades: List) -> Dict[str, Any]:
    """Calculate trading statistics"""
    
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_profit": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0
        }
    
    total_trades = len(trades)
    winning_trades = 0
    losing_trades = 0
    total_pnl = 0.0
    total_profit = 0.0
    total_loss = 0.0
    
    for trade in trades:
        if trade.status == "filled" and hasattr(trade, "pnl") and trade.pnl is not None:
            total_pnl += trade.pnl
            
            if trade.pnl > 0:
                winning_trades += 1
                total_profit += trade.pnl
            elif trade.pnl < 0:
                losing_trades += 1
                total_loss += abs(trade.pnl)
    
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
    avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0
    
    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞"
    }
