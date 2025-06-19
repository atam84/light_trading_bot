# src/interfaces/web/app.py

"""
Updated Web Application with Real Trading Integration
Connects frontend to actual trading engine and ccxt-gateway
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import our modules
from .trading_api import router as trading_router, init_trading_api
from .auth import auth_router, get_current_user, create_access_token
from ...core.trading_engine import TradingEngine
from ...clients.ccxt_client import CCXTClient
from ...clients.quickchart_client import QuickChartClient
from ...database.connection import DatabaseConnection
from ...database.repositories import (
    UserRepository, 
    ExchangeRepository, 
    StrategyRepository,
    TradeRepository
)
from ...utils.trading_helpers import (
    get_portfolio_summary,
    get_market_overview,
    calculate_risk_metrics,
    format_currency,
    format_percentage
)
from ...core.config_manager import ConfigManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Light Trading Bot",
    description="Advanced trading bot with backtesting, paper trading, and live trading",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="src/interfaces/web/static"), name="static")
templates = Jinja2Templates(directory="src/interfaces/web/templates")

# Global instances
trading_engine: Optional[TradingEngine] = None
ccxt_client: Optional[CCXTClient] = None
quickchart_client: Optional[QuickChartClient] = None
config_manager: Optional[ConfigManager] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(trading_router)

@app.on_event("startup")
async def startup_event():
    """Initialize all services on startup"""
    global trading_engine, ccxt_client, quickchart_client, config_manager
    
    try:
        logger.info("Starting up trading bot web application...")
        
        # Initialize configuration
        config_manager = ConfigManager()
        await config_manager.load_config()
        
        # Initialize database
        db = DatabaseConnection()
        await db.connect()
        
        # Initialize clients
        ccxt_client = CCXTClient()
        quickchart_client = QuickChartClient()
        
        # Initialize trading engine
        trading_engine = TradingEngine(config_manager)
        await trading_engine.initialize()
        
        # Initialize trading API with clients
        init_trading_api(trading_engine, ccxt_client)
        
        logger.info("Trading bot web application started successfully!")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global trading_engine
    
    try:
        if trading_engine:
            await trading_engine.stop()
        logger.info("Trading bot web application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Authentication routes
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

# Main dashboard route  
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    # Check if user is authenticated
    user = await get_optional_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request):
    """Trading interface page"""
    return templates.TemplateResponse("trading.html", {"request": request})

@app.get("/strategies", response_class=HTMLResponse)
async def strategies_page(request: Request):
    """Strategy management page"""
    return templates.TemplateResponse("strategies.html", {"request": request})

@app.get("/backtesting", response_class=HTMLResponse)
async def backtesting_page(request: Request):
    """Backtesting interface page"""
    return templates.TemplateResponse("backtesting.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    return templates.TemplateResponse("settings.html", {"request": request})

# API Routes for Dashboard Data

@app.get("/api/dashboard/summary")
async def get_dashboard_summary(user = Depends(get_current_user)):
    """Get dashboard summary with real data"""
    try:
        # Get portfolio summary
        portfolio = await get_portfolio_summary(
            user_id=str(user.id),
            ccxt_client=ccxt_client,
            exchange='kucoin'
        )
        
        # Get market overview for popular symbols
        market_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
        market_data = await get_market_overview(market_symbols, ccxt_client)
        
        # Get recent activity
        trade_repo = TradeRepository()
        recent_trades = await trade_repo.get_user_trades(user_id=str(user.id), limit=5)
        
        return {
            "portfolio": {
                "total_value": portfolio['summary']['position_values'],
                "total_pnl": portfolio['summary']['total_pnl'],
                "unrealized_pnl": portfolio['summary']['total_unrealized_pnl'],
                "realized_pnl": portfolio['summary']['total_realized_pnl'],
                "open_positions": portfolio['summary']['total_positions']
            },
            "market_overview": market_data,
            "recent_trades": [
                {
                    "id": str(trade.id),
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "amount": trade.amount,
                    "price": trade.price,
                    "timestamp": trade.timestamp.isoformat(),
                    "status": trade.status
                }
                for trade in recent_trades
            ],
            "performance": portfolio['performance']
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/balance")
async def get_portfolio_balance(
    exchange: str = 'kucoin',
    user = Depends(get_current_user)
):
    """Get real portfolio balance from exchange"""
    try:
        # Get exchange configuration
        exchange_repo = ExchangeRepository()
        user_exchange = await exchange_repo.get_by_user_and_name(str(user.id), exchange)
        
        if not user_exchange:
            return {
                "total_balance": 0,
                "available_balance": 0,
                "used_balance": 0,
                "positions": [],
                "error": "Exchange not configured"
            }
        
        # Get balance from exchange
        balance = await ccxt_client.get_balance(
            exchange=exchange,
            api_key=user_exchange.api_key_encrypted,
            api_secret=user_exchange.api_secret_encrypted
        )
        
        # Process balance data
        positions = []
        total_balance = 0
        used_balance = 0
        
        for asset, asset_balance in balance.items():
            if asset_balance.get('total', 0) > 0:
                total = asset_balance['total']
                free = asset_balance['free']
                used = asset_balance['used']
                
                # Get USD value
                usd_value = total
                if asset not in ['USD', 'USDT', 'USDC']:
                    try:
                        ticker = await ccxt_client.get_ticker(f"{asset}/USDT", exchange)
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
        
        return {
            "total_balance": total_balance,
            "available_balance": total_balance - used_balance,
            "used_balance": used_balance,
            "positions": positions
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio balance: {str(e)}")
        return {
            "total_balance": 0,
            "available_balance": 0,
            "used_balance": 0,
            "positions": [],
            "error": str(e)
        }

@app.get("/api/strategies/active")
async def get_active_strategies(user = Depends(get_current_user)):
    """Get active strategies for user"""
    try:
        strategy_repo = StrategyRepository()
        strategies = await strategy_repo.get_user_strategies(str(user.id), active_only=True)
        
        return [
            {
                "id": str(strategy.id),
                "name": strategy.name,
                "strategy_type": strategy.strategy_type,
                "active": strategy.active,
                "performance": {
                    "total_trades": 0,  # Will be calculated from actual trades
                    "win_rate": 0,
                    "total_pnl": 0
                }
            }
            for strategy in strategies
        ]
        
    except Exception as e:
        logger.error(f"Error getting active strategies: {str(e)}")
        return []

@app.post("/api/strategies/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    user = Depends(get_current_user)
):
    """Activate a trading strategy"""
    try:
        strategy_repo = StrategyRepository()
        
        # Get strategy
        strategy = await strategy_repo.get_by_id(strategy_id)
        if not strategy or strategy.user_id != str(user.id):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Activate strategy in trading engine
        if trading_engine:
            await trading_engine.activate_strategy(strategy_id)
        
        # Update database
        await strategy_repo.update(strategy_id, {"active": True})
        
        return {"success": True, "message": f"Strategy {strategy.name} activated"}
        
    except Exception as e:
        logger.error(f"Error activating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bot/start")
async def start_bot(
    mode: str = "paper",
    user = Depends(get_current_user)
):
    """Start the trading bot"""
    try:
        if trading_engine:
            await trading_engine.start(mode=mode)
            return {"success": True, "message": f"Bot started in {mode} mode"}
        else:
            raise HTTPException(status_code=500, detail="Trading engine not available")
            
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bot/stop")
async def stop_bot(user = Depends(get_current_user)):
    """Stop the trading bot"""
    try:
        if trading_engine:
            await trading_engine.stop()
            return {"success": True, "message": "Bot stopped successfully"}
        else:
            raise HTTPException(status_code=500, detail="Trading engine not available")
            
    except Exception as e:
        logger.error(f"Error stopping bot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bot/status")
async def get_bot_status(user = Depends(get_current_user)):
    """Get trading bot status"""
    try:
        if trading_engine:
            status = await trading_engine.get_status()
            return {
                "running": status.get("running", False),
                "mode": status.get("mode", "stopped"),
                "active_strategies": status.get("active_strategies", 0),
                "uptime": status.get("uptime", 0),
                "last_update": datetime.utcnow().isoformat()
            }
        else:
            return {
                "running": False,
                "mode": "stopped",
                "active_strategies": 0,
                "uptime": 0,
                "last_update": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting bot status: {str(e)}")
        return {
            "running": False,
            "mode": "error",
            "active_strategies": 0,
            "uptime": 0,
            "error": str(e)
        }

# WebSocket endpoint for real-time updates
@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic updates
            if ccxt_client:
                # Get market data for popular symbols
                symbols = ['BTC/USDT', 'ETH/USDT']
                for symbol in symbols:
                    try:
                        ticker = await ccxt_client.get_ticker(symbol, 'kucoin')
                        await websocket.send_text(f"price_update:{symbol}:{ticker['last']}")
                    except:
                        pass
            
            await asyncio.sleep(5)  # Update every 5 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "trading_engine": trading_engine is not None,
            "ccxt_client": ccxt_client is not None,
            "quickchart_client": quickchart_client is not None
        }
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.utcnow().isoformat()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "timestamp": datetime.utcnow().isoformat()}
    )

def run_web_app(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Run the web application"""
    uvicorn.run(
        "src.interfaces.web.app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )

if __name__ == "__main__":
    run_web_app(debug=True)
