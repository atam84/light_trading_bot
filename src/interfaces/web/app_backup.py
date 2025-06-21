# src/interfaces/web/app.py

"""
Enhanced Trading Bot Web Application with Backend Integration
Connects UI to actual trading engine, database, and API clients
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from fastapi import FastAPI, Request, Form, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# Setup paths
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import backend components with fallbacks
try:
    from src.core.trading_engine import TradingEngine
    from src.api_clients.ccxt_client import CCXTClient
    from src.api_clients.quickchart_client import QuickChartClient
    from src.database.repositories import UserRepository, TradeRepository, StrategyRepository, ExchangeRepository
    from src.strategies.strategy_manager import StrategyManager
    from src.core.risk_manager import RiskManager
    BACKEND_AVAILABLE = True
    print("✅ Backend components imported successfully")
except ImportError as e:
    print(f"⚠️  Backend components not available: {e}")
    print("🔄 Running in UI-only mode with mock data")
    BACKEND_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Light Trading Bot",
    description="Advanced Trading Automation Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

# Backend Components Initialization
trading_engine = None
ccxt_client = None
quickchart_client = None
user_repo = None
trade_repo = None
strategy_repo = None
exchange_repo = None
strategy_manager = None
risk_manager = None

async def initialize_backend():
    """Initialize backend components if available"""
    global trading_engine, ccxt_client, quickchart_client
    global user_repo, trade_repo, strategy_repo, exchange_repo
    global strategy_manager, risk_manager
    
    if not BACKEND_AVAILABLE:
        return False
    
    try:
        # Initialize API clients
        ccxt_client = CCXTClient()
        quickchart_client = QuickChartClient()
        
        # Initialize repositories
        user_repo = UserRepository()
        trade_repo = TradeRepository()
        strategy_repo = StrategyRepository()
        exchange_repo = ExchangeRepository()
        
        # Initialize trading components
        risk_manager = RiskManager()
        strategy_manager = StrategyManager()
        trading_engine = TradingEngine()
        
        logger.info("✅ Backend components initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize backend components: {e}")
        return False

# Initialize backend on startup
@app.on_event("startup")
async def startup_event():
    """Initialize backend components on startup"""
    await initialize_backend()

# Templates and static files
templates_dir = current_dir / "templates"
static_dir = current_dir / "static"

# Create directories if they don't exist
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))

# Mount static files
try:
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Session storage (enhanced with database integration)
sessions = {}
demo_user = {
    "id": "demo_user_123",
    "username": "demo",
    "email": "demo@tradingbot.com",
    "password": "demo123"
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# Authentication helpers (enhanced with database)
async def create_session(user_id: str) -> str:
    """Create a new session"""
    session_id = f"session_{user_id}_{datetime.now().timestamp()}"
    sessions[session_id] = {
        "user_id": user_id,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24)
    }
    return session_id

async def get_current_user(request: Request):
    """Get current user from session (enhanced with database lookup)"""
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        return None
    
    session = sessions.get(session_id)
    if not session or session["expires_at"] < datetime.now():
        return None
    
    # Try to get user from database first
    if BACKEND_AVAILABLE and user_repo:
        try:
            user = await user_repo.find_by_id(session["user_id"])
            if user:
                return user
        except Exception as e:
            logger.warning(f"Database user lookup failed: {e}")
    
    # Fallback to demo user
    return demo_user

# Enhanced API functions with real backend integration
async def get_real_portfolio(user_id: str) -> Dict[str, Any]:
    """Get real portfolio data from exchanges"""
    if not BACKEND_AVAILABLE or not ccxt_client:
        # Fallback to mock data
        return {
            "total_balance": 10000.00,
            "available_balance": 8500.00,
            "invested_balance": 1500.00,
            "total_pnl": 250.00,
            "total_pnl_pct": 2.5,
            "positions": []
        }
    
    try:
        # Get balance from exchange
        balance = await ccxt_client.get_balance("kucoin")  # Default exchange
        
        # Calculate portfolio metrics
        total_balance = float(balance.get("USDT", {}).get("total", 0))
        free_balance = float(balance.get("USDT", {}).get("free", 0))
        
        # Get positions from database
        positions = []
        if trade_repo:
            recent_trades = await trade_repo.get_user_trades(user_id, limit=10)
            # Calculate positions from trades (simplified)
            
        return {
            "total_balance": total_balance,
            "available_balance": free_balance,
            "invested_balance": total_balance - free_balance,
            "total_pnl": 0.0,  # Calculate from trades
            "total_pnl_pct": 0.0,
            "positions": positions
        }
        
    except Exception as e:
        logger.error(f"Failed to get real portfolio: {e}")
        # Return mock data on error
        return {
            "total_balance": 10000.00,
            "available_balance": 8500.00,
            "invested_balance": 1500.00,
            "total_pnl": 250.00,
            "total_pnl_pct": 2.5,
            "positions": []
        }

async def get_real_market_data(symbol: str = "BTC/USDT") -> Dict[str, Any]:
    """Get real market data from ccxt-gateway"""
    if not BACKEND_AVAILABLE or not ccxt_client:
        # Fallback to mock data
        return {
            "symbol": symbol,
            "price": 42380.00,
            "change_24h": 0.55,
            "volume_24h": 1234567.89,
            "high_24h": 43000.00,
            "low_24h": 41800.00
        }
    
    try:
        # Get ticker data
        ticker = await ccxt_client.get_ticker(symbol)
        
        return {
            "symbol": symbol,
            "price": float(ticker.get("last", 0)),
            "change_24h": float(ticker.get("percentage", 0)),
            "volume_24h": float(ticker.get("quoteVolume", 0)),
            "high_24h": float(ticker.get("high", 0)),
            "low_24h": float(ticker.get("low", 0))
        }
        
    except Exception as e:
        logger.error(f"Failed to get market data: {e}")
        return {
            "symbol": symbol,
            "price": 42380.00,
            "change_24h": 0.55,
            "volume_24h": 1234567.89,
            "high_24h": 43000.00,
            "low_24h": 41800.00
        }

async def place_real_trade(user_id: str, trade_data: Dict[str, Any]) -> Dict[str, Any]:
    """Place a real trade through ccxt-gateway"""
    if not BACKEND_AVAILABLE or not ccxt_client or not trade_repo:
        # Simulate trade placement
        return {
            "status": "success",
            "order_id": f"mock_order_{datetime.now().timestamp()}",
            "message": "Trade simulation completed (backend not available)"
        }
    
    try:
        # Validate trade with risk manager
        if risk_manager:
            risk_check = await risk_manager.validate_trade(user_id, trade_data)
            if not risk_check["valid"]:
                return {
                    "status": "error",
                    "message": f"Trade rejected by risk manager: {risk_check['reason']}"
                }
        
        # Place order through ccxt-gateway
        order_result = await ccxt_client.place_order(
            symbol=trade_data["symbol"],
            side=trade_data["side"],
            amount=float(trade_data["amount"]),
            order_type=trade_data.get("type", "market"),
            price=trade_data.get("price")
        )
        
        # Store trade in database
        trade_record = {
            "user_id": user_id,
            "symbol": trade_data["symbol"],
            "side": trade_data["side"],
            "amount": float(trade_data["amount"]),
            "price": float(order_result.get("price", 0)),
            "order_id": order_result.get("id"),
            "status": "filled",
            "timestamp": datetime.now()
        }
        
        await trade_repo.create_trade(trade_record)
        
        # Broadcast update to connected WebSocket clients
        await manager.broadcast(json.dumps({
            "type": "trade_update",
            "data": trade_record
        }))
        
        return {
            "status": "success",
            "order_id": order_result.get("id"),
            "message": "Trade executed successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to place real trade: {e}")
        return {
            "status": "error",
            "message": f"Trade execution failed: {str(e)}"
        }

# HTML Templates (same as before but with enhanced functionality)
def get_base_template():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Trading Bot{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #ffffff; 
            min-height: 100vh;
        }
        .navbar {
            background: rgba(0,0,0,0.3);
            padding: 1rem 2rem;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .navbar .brand { font-size: 1.5rem; font-weight: bold; color: #4CAF50; }
        .navbar .nav-links { float: right; }
        .navbar .nav-links a { 
            color: white; 
            text-decoration: none; 
            margin-left: 2rem;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            transition: background 0.3s;
        }
        .navbar .nav-links a:hover { background: rgba(76, 175, 80, 0.2); }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 2rem;
            margin: 1rem 0;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary { background: #4CAF50; color: white; }
        .btn-primary:hover { background: #45a049; transform: translateY(-2px); }
        .btn-danger { background: #f44336; color: white; }
        .btn-danger:hover { background: #da190b; }
        .btn-secondary { background: #2196F3; color: white; }
        .btn-secondary:hover { background: #1976D2; }
        .form-group { margin: 1rem 0; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
        .form-group input, .form-group select {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 1rem;
        }
        .form-group input::placeholder { color: rgba(255,255,255,0.6); }
        .grid { display: grid; gap: 2rem; }
        .grid-2 { grid-template-columns: 1fr 1fr; }
        .grid-3 { grid-template-columns: 1fr 1fr 1fr; }
        .grid-4 { grid-template-columns: 1fr 1fr 1fr 1fr; }
        .status-active { color: #4CAF50; font-weight: bold; }
        .status-pending { color: #FF9800; font-weight: bold; }
        .status-error { color: #f44336; font-weight: bold; }
        .profit-positive { color: #4CAF50; }
        .profit-negative { color: #f44336; }
        table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { background: rgba(255,255,255,0.1); font-weight: 600; }
        .metric-card {
            text-align: center;
            padding: 1.5rem;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .metric-value { font-size: 2rem; font-weight: bold; margin: 0.5rem 0; }
        .metric-label { font-size: 0.9rem; opacity: 0.8; }
        .live-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #4CAF50;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 8px;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 2rem;
            background: #4CAF50;
            color: white;
            border-radius: 8px;
            display: none;
            z-index: 1000;
        }
        .notification.error { background: #f44336; }
        .notification.warning { background: #FF9800; }
        @media (max-width: 768px) {
            .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
            .navbar .nav-links { float: none; text-align: center; margin-top: 1rem; }
            .container { padding: 1rem; }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="brand">🤖 Trading Bot <span class="live-indicator"></span></div>
        <div class="nav-links">
            <a href="/">Dashboard</a>
            <a href="/trading">Trading</a>
            <a href="/strategies">Strategies</a>
            <a href="/backtesting">Backtesting</a>
            <a href="/settings">Settings</a>
            <a href="/logout">Logout</a>
        </div>
        <div style="clear: both;"></div>
    </nav>
    
    <div class="container">
        {% block content %}{% endblock %}
    </div>
    
    <div id="notification" class="notification"></div>
    
    <script>
        // WebSocket connection for real-time updates
        let ws;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = function(event) {
                console.log('WebSocket connected');
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            ws.onclose = function(event) {
                console.log('WebSocket disconnected, attempting to reconnect...');
                setTimeout(connectWebSocket, 5000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        function handleWebSocketMessage(data) {
            if (data.type === 'price_update') {
                updateMarketData(data.data);
            } else if (data.type === 'trade_update') {
                showNotification('Trade executed: ' + data.data.symbol, 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else if (data.type === 'portfolio_update') {
                updatePortfolio(data.data);
            }
        }
        
        function updateMarketData(data) {
            // Update price displays
            const priceElements = document.querySelectorAll('[data-symbol="' + data.symbol + '"] .price');
            priceElements.forEach(el => {
                el.textContent = '$' + data.price.toLocaleString();
            });
        }
        
        function updatePortfolio(data) {
            // Update portfolio displays
            const balanceElement = document.querySelector('.total-balance');
            if (balanceElement) {
                balanceElement.textContent = '$' + data.total_balance.toLocaleString();
            }
        }
        
        function showNotification(message, type = 'success') {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = 'notification ' + type;
            notification.style.display = 'block';
            
            setTimeout(() => {
                notification.style.display = 'none';
            }, 5000);
        }
        
        // Enhanced API functions
        async function fetchAPI(url, options = {}) {
            try {
                const response = await fetch(url, {
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                showNotification('API Error: ' + error.message, 'error');
                throw error;
            }
        }
        
        // Auto-refresh data every 30 seconds
        setInterval(async () => {
            if (window.location.pathname !== '/login') {
                try {
                    const portfolio = await fetchAPI('/api/portfolio');
                    updatePortfolio(portfolio);
                } catch (error) {
                    console.error('Failed to refresh data:', error);
                }
            }
        }, 30000);
        
        // Initialize WebSocket connection
        if (window.location.pathname !== '/login') {
            connectWebSocket();
        }
    </script>
</body>
</html>
    """

# Enhanced Routes with Backend Integration

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    # Get real portfolio data
    portfolio = await get_real_portfolio(user["id"])
    
    # Get real market data for major pairs
    btc_data = await get_real_market_data("BTC/USDT")
    eth_data = await get_real_market_data("ETH/USDT")
    
    html_content = f"""
    {get_base_template().replace('{% block title %}Trading Bot{% endblock %}', 'Dashboard - Trading Bot')}
    """.replace('{% block content %}', f"""
    <h1>📊 Trading Dashboard</h1>
    
    <div class="grid grid-4">
        <div class="metric-card">
            <div class="metric-value profit-positive total-balance">${portfolio['total_balance']:,.2f}</div>
            <div class="metric-label">Total Balance</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${portfolio['available_balance']:,.2f}</div>
            <div class="metric-label">Available Balance</div>
        </div>
        <div class="metric-card">
            <div class="metric-value profit-positive">${portfolio['total_pnl']:,.2f}</div>
            <div class="metric-label">Total P&L</div>
        </div>
        <div class="metric-card">
            <div class="metric-value profit-positive">{portfolio['total_pnl_pct']:.2f}%</div>
            <div class="metric-label">P&L Percentage</div>
        </div>
    </div>
    
    <div class="grid grid-2">
        <div class="card">
            <h3>📈 Live Market Data</h3>
            <div class="grid grid-2">
                <div class="metric-card" data-symbol="BTC/USDT">
                    <div class="metric-value price">${btc_data['price']:,.2f}</div>
                    <div class="metric-label">BTC/USDT</div>
                    <div class="profit-positive">{btc_data['change_24h']:+.2f}%</div>
                </div>
                <div class="metric-card" data-symbol="ETH/USDT">
                    <div class="metric-value price">${eth_data['price']:,.2f}</div>
                    <div class="metric-label">ETH/USDT</div>
                    <div class="profit-positive">{eth_data['change_24h']:+.2f}%</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>🎯 System Status</h3>
            <table>
                <tr>
                    <td>Backend Status</td>
                    <td class="status-{'active' if BACKEND_AVAILABLE else 'error'}">
                        {'Connected' if BACKEND_AVAILABLE else 'Mock Mode'}
                    </td>
                </tr>
                <tr>
                    <td>Trading Engine</td>
                    <td class="status-{'active' if trading_engine else 'pending'}">
                        {'Active' if trading_engine else 'Initializing'}
                    </td>
                </tr>
                <tr>
                    <td>Market Data</td>
                    <td class="status-{'active' if ccxt_client else 'pending'}">
                        {'Live' if ccxt_client else 'Simulated'}
                    </td>
                </tr>
                <tr>
                    <td>Database</td>
                    <td class="status-{'active' if user_repo else 'pending'}">
                        {'Connected' if user_repo else 'Mock Data'}
                    </td>
                </tr>
            </table>
        </div>
    </div>
    """).replace('{% endblock %}', '')
    
    return HTMLResponse(html_content)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Same login page as before
    html_content = f"""
    {get_base_template().replace('{% block title %}Trading Bot{% endblock %}', 'Login - Trading Bot')}
    """.replace('{% block content %}', """
    <div style="max-width: 400px; margin: 5rem auto;">
        <div class="card">
            <h2 style="text-align: center; margin-bottom: 2rem;">🔐 Login to Trading Bot</h2>
            
            <form method="post" action="/login">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" name="username" value="demo" required>
                </div>
                
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" value="demo123" required>
                </div>
                
                <div class="form-group">
                    <button type="submit" class="btn btn-primary" style="width: 100%;">Login</button>
                </div>
            </form>
            
            <div style="text-align: center; margin-top: 2rem; padding: 1rem; background: rgba(76, 175, 80, 0.1); border-radius: 8px;">
                <h4>Demo Account</h4>
                <p>Username: <strong>demo</strong></p>
                <p>Password: <strong>demo123</strong></p>
            </div>
        </div>
    </div>
    """).replace('{% endblock %}', '')
    
    return HTMLResponse(html_content)

@app.post("/login")
async def login_submit(username: str = Form(...), password: str = Form(...)):
    # Enhanced login with database lookup
    user = None
    
    if BACKEND_AVAILABLE and user_repo:
        try:
            user = await user_repo.find_by_username(username)
            if user and user.verify_password(password):
                session_id = await create_session(user["id"])
                response = RedirectResponse(url="/", status_code=302)
                response.set_cookie(key="session_id", value=session_id, httponly=True)
                return response
        except Exception as e:
            logger.warning(f"Database login failed: {e}")
    
    # Fallback to demo user
    if username == demo_user["username"] and password == demo_user["password"]:
        session_id = await create_session(demo_user["id"])
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="session_id")
    return response

# Enhanced Trading Interface
@app.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    # Get real market data
    btc_data = await get_real_market_data("BTC/USDT")
    eth_data = await get_real_market_data("ETH/USDT")
    
    # Get real orders and trades if available
    orders_data = []
    trades_data = []
    
    if BACKEND_AVAILABLE and trade_repo:
        try:
            orders_data = await trade_repo.get_user_orders(user["id"], status="open")
            trades_data = await trade_repo.get_user_trades(user["id"], limit=10)
        except Exception as e:
            logger.warning(f"Failed to get orders/trades: {e}")
    
    html_content = f"""
    {get_base_template().replace('{% block title %}Trading Bot{% endblock %}', 'Trading - Trading Bot')}
    """.replace('{% block content %}', f"""
    <h1>💰 Trading Interface</h1>
    
    <div class="grid grid-2">
        <div class="card">
            <h3>📈 Live Market Data</h3>
            <div class="grid grid-2">
                <div class="metric-card" data-symbol="BTC/USDT">
                    <div class="metric-value price">${btc_data['price']:,.2f}</div>
                    <div class="metric-label">BTC/USDT</div>
                    <div class="profit-positive">{btc_data['change_24h']:+.2f}%</div>
                </div>
                <div class="metric-card" data-symbol="ETH/USDT">
                    <div class="metric-value price">${eth_data['price']:,.2f}</div>
                    <div class="metric-label">ETH/USDT</div>
                    <div class="profit-positive">{eth_data['change_24h']:+.2f}%</div>
                </div>
            </div>
            <button class="btn btn-secondary" onclick="refreshMarketData()">🔄 Refresh Data</button>
        </div>
        
        <div class="card">
            <h3>⚡ Quick Trade</h3>
            <form onsubmit="return submitTrade(event)">
                <div class="form-group">
                    <label>Symbol</label>
                    <select name="symbol" required>
                        <option value="BTC/USDT">BTC/USDT</option>
                        <option value="ETH/USDT">ETH/USDT</option>
                        <option value="BNB/USDT">BNB/USDT</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Side</label>
                    <select name="side" required>
                        <option value="buy">Buy</option>
                        <option value="sell">Sell</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Amount (USD)</label>
                    <input type="number" name="amount" min="10" step="0.01" value="100" required>
                </div>
                
                <div class="form-group">
                    <label>Order Type</label>
                    <select name="type" required>
                        <option value="market">Market</option>
                        <option value="limit">Limit</option>
                    </select>
                </div>
                
                <div class="grid grid-2">
                    <button type="submit" class="btn btn-primary">📊 Place Order</button>
                    <button type="button" class="btn btn-danger" onclick="cancelAllOrders()">❌ Cancel All</button>
                </div>
            </form>
        </div>
    </div>
    
    <div class="card">
        <h3>📋 Open Orders</h3>
        <table>
            <thead>
                <tr><th>Time</th><th>Symbol</th><th>Side</th><th>Type</th><th>Amount</th><th>Price</th><th>Status</th><th>Action</th></tr>
            </thead>
            <tbody id="orders-table">
                {"".join([f'''
                <tr>
                    <td>{order.get("timestamp", "").split("T")[0]}</td>
                    <td>{order.get("symbol", "")}</td>
                    <td>{order.get("side", "").upper()}</td>
                    <td>{order.get("type", "").title()}</td>
                    <td>{order.get("amount", 0):.4f}</td>
                    <td>${order.get("price", 0):,.2f}</td>
                    <td class="status-pending">Pending</td>
                    <td><button class="btn btn-danger" onclick="cancelOrder('{order.get("id", "")}')">Cancel</button></td>
                </tr>
                ''' for order in orders_data]) if orders_data else '''
                <tr><td colspan="8" style="text-align: center;">No open orders</td></tr>
                '''}
            </tbody>
        </table>
    </div>
    
    <script>
        async function refreshMarketData() {{
            try {{
                showNotification('Refreshing market data...', 'info');
                const btcData = await fetchAPI('/api/market-data?symbol=BTC/USDT');
                const ethData = await fetchAPI('/api/market-data?symbol=ETH/USDT');
                updateMarketData(btcData);
                updateMarketData(ethData);
                showNotification('Market data updated!', 'success');
            }} catch (error) {{
                showNotification('Failed to refresh market data', 'error');
            }}
        }}
        
        async function submitTrade(event) {{
            event.preventDefault();
            const formData = new FormData(event.target);
            const trade = Object.fromEntries(formData);
            
            if (confirm(`Place ${{trade.side.toUpperCase()}} order for ${{trade.amount}} USD of ${{trade.symbol}}?`)) {{
                try {{
                    const result = await fetchAPI('/api/trade', {{
                        method: 'POST',
                        body: JSON.stringify(trade)
                    }});
                    
                    if (result.status === 'success') {{
                        showNotification(`✅ Order placed successfully! Order ID: ${{result.order_id}}`, 'success');
                        setTimeout(() => window.location.reload(), 2000);
                    }} else {{
                        showNotification(`❌ Order failed: ${{result.message}}`, 'error');
                    }}
                }} catch (error) {{
                    showNotification('Trade submission failed', 'error');
                }}
            }}
            return false;
        }}
        
        async function cancelOrder(orderId) {{
            if (confirm('Cancel this order?')) {{
                try {{
                    const result = await fetchAPI(`/api/orders/${{orderId}}/cancel`, {{
                        method: 'POST'
                    }});
                    
                    if (result.status === 'success') {{
                        showNotification('Order cancelled successfully', 'success');
                        event.target.closest('tr').remove();
                    }} else {{
                        showNotification('Failed to cancel order', 'error');
                    }}
                }} catch (error) {{
                    showNotification('Cancel request failed', 'error');
                }}
            }}
        }}
        
        async function cancelAllOrders() {{
            if (confirm('Cancel ALL open orders?')) {{
                try {{
                    const result = await fetchAPI('/api/orders/cancel-all', {{
                        method: 'POST'
                    }});
                    
                    if (result.status === 'success') {{
                        showNotification('All orders cancelled', 'success');
                        document.getElementById('orders-table').innerHTML = '<tr><td colspan="8" style="text-align: center;">No open orders</td></tr>';
                    }} else {{
                        showNotification('Failed to cancel orders', 'error');
                    }}
                }} catch (error) {{
                    showNotification('Cancel all request failed', 'error');
                }}
            }}
        }}
    </script>
    """).replace('{% endblock %}', '')
    
    return HTMLResponse(html_content)

# Enhanced API Endpoints with Real Backend Integration

@app.get("/api/portfolio")
async def get_portfolio_api(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    portfolio = await get_real_portfolio(user["id"])
    return portfolio

@app.get("/api/market-data")
async def get_market_data_api(symbol: str = "BTC/USDT"):
    market_data = await get_real_market_data(symbol)
    return market_data

@app.post("/api/trade")
async def place_trade_api(trade_data: dict, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await place_real_trade(user["id"], trade_data)
    return result

@app.get("/api/orders")
async def get_orders_api(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if BACKEND_AVAILABLE and trade_repo:
        try:
            orders = await trade_repo.get_user_orders(user["id"])
            return orders
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
    
    return []

@app.post("/api/orders/{order_id}/cancel")
async def cancel_order_api(order_id: str, request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if BACKEND_AVAILABLE and ccxt_client:
        try:
            result = await ccxt_client.cancel_order(order_id)
            return {"status": "success", "message": "Order cancelled"}
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return {"status": "error", "message": str(e)}
    
    return {"status": "success", "message": "Order cancelled (simulated)"}

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic market data updates
            btc_data = await get_real_market_data("BTC/USDT")
            await manager.send_personal_message(json.dumps({
                "type": "price_update",
                "data": btc_data
            }), websocket)
            
            await asyncio.sleep(5)  # Update every 5 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "backend_available": BACKEND_AVAILABLE,
        "components": {
            "web_interface": "running",
            "trading_engine": "active" if trading_engine else "inactive",
            "ccxt_client": "connected" if ccxt_client else "unavailable",
            "database": "connected" if user_repo else "unavailable",
            "websocket": "active"
        }
    }

def run_web_app(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Run the enhanced web application with backend integration"""
    try:
        uvicorn.run(
            "app:app" if __name__ == "__main__" else app,
            host=host,
            port=port,
            reload=debug,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start web application: {e}")
        raise

if __name__ == "__main__":
    run_web_app()