# src/interfaces/web/trading_api.py

"""
Real Trading Backend API Implementation
Connects web interface to actual trading engine and ccxt-gateway
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, WebSocket
from pydantic import BaseModel, validator
import json

from ...core import TradingEngine
from ...clients.ccxt_client import CCXTClient
from ...database import (
    TradeRepository, 
    UserRepository, 
    ExchangeRepository,
    StrategyRepository
)
from ...core import RiskManager
from ...utils import format_currency, calculate_pnl
from .auth import get_current_user

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class OrderRequest(BaseModel):
    symbol: str
    side: str  # 'buy' or 'sell'
    type: str  # 'market' or 'limit'
    amount: float
    price: Optional[float] = None
    exchange: str = 'kucoin'
    
    @validator('side')
    def validate_side(cls, v):
        if v not in ['buy', 'sell']:
            raise ValueError('Side must be buy or sell')
        return v
    
    @validator('type')
    def validate_type(cls, v):
        if v not in ['market', 'limit']:
            raise ValueError('Type must be market or limit')
        return v

class MarketDataResponse(BaseModel):
    symbol: str
    price: float
    change_24h: float
    change_24h_pct: float
    volume_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime

class TradeResponse(BaseModel):
    id: str
    symbol: str
    side: str
    type: str
    amount: float
    price: float
    status: str
    timestamp: datetime
    exchange: str
    pnl: Optional[float] = None

class PortfolioResponse(BaseModel):
    total_balance: float
    available_balance: float
    used_balance: float
    positions: List[Dict[str, Any]]
    pnl_24h: float
    pnl_total: float

# Create router
router = APIRouter(prefix="/api/trading", tags=["trading"])

# Global instances (will be injected properly in main app)
trading_engine: Optional[TradingEngine] = None
ccxt_client: Optional[CCXTClient] = None

def get_trading_engine():
    """Dependency to get trading engine instance"""
    if trading_engine is None:
        raise HTTPException(status_code=500, detail="Trading engine not initialized")
    return trading_engine

def get_ccxt_client():
    """Dependency to get CCXT client instance"""
    if ccxt_client is None:
        raise HTTPException(status_code=500, detail="CCXT client not initialized")
    return ccxt_client

@router.post("/order", response_model=TradeResponse)
async def place_order(
    order: OrderRequest,
    user = Depends(get_current_user),
    engine = Depends(get_trading_engine),
    client = Depends(get_ccxt_client)
):
    """
    Place a real trading order via ccxt-gateway
    """
    try:
        logger.info(f"Placing order: {order.dict()}")
        
        # Validate user has exchange configured
        exchange_repo = ExchangeRepository()
        user_exchange = await exchange_repo.get_by_user_and_name(user.id, order.exchange)
        if not user_exchange:
            raise HTTPException(
                status_code=400, 
                detail=f"Exchange {order.exchange} not configured for user"
            )
        
        # Risk management check
        risk_manager = RiskManager()
        risk_check = await risk_manager.validate_trade(
            user_id=user.id,
            symbol=order.symbol,
            side=order.side,
            amount=order.amount,
            price=order.price
        )
        
        if not risk_check.allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Risk check failed: {risk_check.reason}"
            )
        
        # Get current market price if market order
        if order.type == 'market':
            ticker = await client.get_ticker(order.symbol, order.exchange)
            order.price = ticker['last']
        
        # Place order via ccxt-gateway
        order_result = await client.place_order(
            symbol=order.symbol,
            side=order.side,
            type=order.type,
            amount=order.amount,
            price=order.price,
            exchange=order.exchange,
            api_key=user_exchange.api_key_encrypted,  # Will be decrypted in client
            api_secret=user_exchange.api_secret_encrypted
        )
        
        # Store trade in database
        trade_repo = TradeRepository()
        trade_data = {
            'user_id': user.id,
            'exchange': order.exchange,
            'symbol': order.symbol,
            'side': order.side,
            'type': order.type,
            'amount': order.amount,
            'price': order.price,
            'filled_amount': order_result.get('filled', 0),
            'status': order_result.get('status', 'pending'),
            'mode': 'live',
            'order_id': order_result.get('id'),
            'fee': order_result.get('fee', 0),
            'timestamp': datetime.utcnow()
        }
        
        saved_trade = await trade_repo.create(trade_data)
        
        # Calculate PnL if it's a sell order
        pnl = None
        if order.side == 'sell':
            pnl = await calculate_pnl(user.id, order.symbol, order.amount, order.price)
        
        return TradeResponse(
            id=str(saved_trade.id),
            symbol=order.symbol,
            side=order.side,
            type=order.type,
            amount=order.amount,
            price=order.price,
            status=trade_data['status'],
            timestamp=trade_data['timestamp'],
            exchange=order.exchange,
            pnl=pnl
        )
        
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-data/{symbol}", response_model=MarketDataResponse)
async def get_market_data(
    symbol: str,
    exchange: str = 'kucoin',
    user = Depends(get_current_user),
    client = Depends(get_ccxt_client)
):
    """
    Get real-time market data for a symbol
    """
    try:
        # Get ticker data
        ticker = await client.get_ticker(symbol, exchange)
        
        # Get 24h stats
        stats_24h = await client.get_24h_stats(symbol, exchange)
        
        return MarketDataResponse(
            symbol=symbol,
            price=ticker['last'],
            change_24h=stats_24h.get('change', 0),
            change_24h_pct=stats_24h.get('percentage', 0),
            volume_24h=stats_24h.get('quoteVolume', 0),
            high_24h=stats_24h.get('high', 0),
            low_24h=stats_24h.get('low', 0),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error getting market data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(
    exchange: str = 'kucoin',
    user = Depends(get_current_user),
    client = Depends(get_ccxt_client)
):
    """
    Get real portfolio balance and positions
    """
    try:
        # Get exchange configuration
        exchange_repo = ExchangeRepository()
        user_exchange = await exchange_repo.get_by_user_and_name(user.id, exchange)
        if not user_exchange:
            raise HTTPException(
                status_code=400,
                detail=f"Exchange {exchange} not configured"
            )
        
        # Get balance from exchange
        balance = await client.get_balance(
            exchange=exchange,
            api_key=user_exchange.api_key_encrypted,
            api_secret=user_exchange.api_secret_encrypted
        )
        
        # Get positions (non-zero balances)
        positions = []
        total_balance = 0
        used_balance = 0
        
        for asset, asset_balance in balance.items():
            if asset_balance.get('total', 0) > 0:
                total = asset_balance['total']
                free = asset_balance['free']
                used = asset_balance['used']
                
                # Get USD value if not USD/USDT
                usd_value = total
                if asset not in ['USD', 'USDT', 'USDC']:
                    try:
                        ticker = await client.get_ticker(f"{asset}/USDT", exchange)
                        usd_value = total * ticker['last']
                    except:
                        usd_value = 0
                
                positions.append({
                    'asset': asset,
                    'total': total,
                    'free': free,
                    'used': used,
                    'usd_value': usd_value
                })
                
                total_balance += usd_value
                used_balance += (used * usd_value / total) if total > 0 else 0
        
        # Calculate PnL
        trade_repo = TradeRepository()
        pnl_24h = await trade_repo.get_pnl_24h(user.id)
        pnl_total = await trade_repo.get_pnl_total(user.id)
        
        return PortfolioResponse(
            total_balance=total_balance,
            available_balance=total_balance - used_balance,
            used_balance=used_balance,
            positions=positions,
            pnl_24h=pnl_24h,
            pnl_total=pnl_total
        )
        
    except Exception as e:
        logger.error(f"Error getting portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades", response_model=List[TradeResponse])
async def get_trade_history(
    limit: int = 50,
    offset: int = 0,
    symbol: Optional[str] = None,
    user = Depends(get_current_user)
):
    """
    Get real trade history from database
    """
    try:
        trade_repo = TradeRepository()
        trades = await trade_repo.get_user_trades(
            user_id=user.id,
            limit=limit,
            offset=offset,
            symbol=symbol
        )
        
        trade_responses = []
        for trade in trades:
            # Calculate PnL for sell trades
            pnl = None
            if trade.side == 'sell':
                pnl = await calculate_pnl(user.id, trade.symbol, trade.amount, trade.price)
            
            trade_responses.append(TradeResponse(
                id=str(trade.id),
                symbol=trade.symbol,
                side=trade.side,
                type=trade.type,
                amount=trade.amount,
                price=trade.price,
                status=trade.status,
                timestamp=trade.timestamp,
                exchange=trade.exchange,
                pnl=pnl
            ))
        
        return trade_responses
        
    except Exception as e:
        logger.error(f"Error getting trade history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders")
async def get_open_orders(
    exchange: str = 'kucoin',
    user = Depends(get_current_user),
    client = Depends(get_ccxt_client)
):
    """
    Get real open orders from exchange
    """
    try:
        # Get exchange configuration
        exchange_repo = ExchangeRepository()
        user_exchange = await exchange_repo.get_by_user_and_name(user.id, exchange)
        if not user_exchange:
            raise HTTPException(
                status_code=400,
                detail=f"Exchange {exchange} not configured"
            )
        
        # Get open orders from exchange
        orders = await client.get_open_orders(
            exchange=exchange,
            api_key=user_exchange.api_key_encrypted,
            api_secret=user_exchange.api_secret_encrypted
        )
        
        return orders
        
    except Exception as e:
        logger.error(f"Error getting open orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    exchange: str = 'kucoin',
    user = Depends(get_current_user),
    client = Depends(get_ccxt_client)
):
    """
    Cancel an open order
    """
    try:
        # Get exchange configuration
        exchange_repo = ExchangeRepository()
        user_exchange = await exchange_repo.get_by_user_and_name(user.id, exchange)
        if not user_exchange:
            raise HTTPException(
                status_code=400,
                detail=f"Exchange {exchange} not configured"
            )
        
        # Cancel order via ccxt-gateway
        result = await client.cancel_order(
            order_id=order_id,
            exchange=exchange,
            api_key=user_exchange.api_key_encrypted,
            api_secret=user_exchange.api_secret_encrypted
        )
        
        # Update trade status in database
        trade_repo = TradeRepository()
        await trade_repo.update_by_order_id(order_id, {'status': 'cancelled'})
        
        return {"success": True, "message": f"Order {order_id} cancelled successfully"}
        
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/market-data/{symbol}")
async def market_data_websocket(websocket: WebSocket, symbol: str, exchange: str = 'kucoin'):
    """
    WebSocket endpoint for real-time market data
    """
    await websocket.accept()
    client = get_ccxt_client()
    
    try:
        while True:
            # Get current market data
            ticker = await client.get_ticker(symbol, exchange)
            stats_24h = await client.get_24h_stats(symbol, exchange)
            
            data = {
                'symbol': symbol,
                'price': ticker['last'],
                'change_24h': stats_24h.get('change', 0),
                'change_24h_pct': stats_24h.get('percentage', 0),
                'volume_24h': stats_24h.get('quoteVolume', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(2)  # Update every 2 seconds
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()

# Initialize function to be called from main app
def init_trading_api(engine: TradingEngine, client: CCXTClient):
    """Initialize trading API with engine and client instances"""
    global trading_engine, ccxt_client
    trading_engine = engine
    ccxt_client = client
    logger.info("Trading API initialized with engine and client")
