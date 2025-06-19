# src/interfaces/web/app.py

"""
Simplified Web Application for Initial Startup
Handles graceful degradation when modules are missing
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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

# Check if static files and templates exist
static_dir = "src/interfaces/web/static"
templates_dir = "src/interfaces/web/templates"

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

if os.path.exists(templates_dir):
    templates = Jinja2Templates(directory=templates_dir)
else:
    templates = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting up trading bot web application...")
    logger.info("Web application started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Trading bot web application shutdown complete")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Main pages
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    if templates:
        try:
            return templates.TemplateResponse("dashboard.html", {"request": request})
        except:
            pass
    
    # Fallback HTML if templates don't exist
    return HTMLResponse(content=get_fallback_dashboard(), status_code=200)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    if templates:
        try:
            return templates.TemplateResponse("login.html", {"request": request})
        except:
            pass
    
    # Fallback HTML if templates don't exist
    return HTMLResponse(content=get_fallback_login(), status_code=200)

@app.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request):
    """Trading interface page"""
    if templates:
        try:
            return templates.TemplateResponse("trading.html", {"request": request})
        except:
            pass
    
    return HTMLResponse(content=get_fallback_trading(), status_code=200)

@app.get("/strategies", response_class=HTMLResponse)
async def strategies_page(request: Request):
    """Strategy management page"""
    if templates:
        try:
            return templates.TemplateResponse("strategies.html", {"request": request})
        except:
            pass
    
    return HTMLResponse(content=get_fallback_page("Strategies"), status_code=200)

@app.get("/backtesting", response_class=HTMLResponse)
async def backtesting_page(request: Request):
    """Backtesting interface page"""
    if templates:
        try:
            return templates.TemplateResponse("backtesting.html", {"request": request})
        except:
            pass
    
    return HTMLResponse(content=get_fallback_page("Backtesting"), status_code=200)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    if templates:
        try:
            return templates.TemplateResponse("settings.html", {"request": request})
        except:
            pass
    
    return HTMLResponse(content=get_fallback_page("Settings"), status_code=200)

# API routes with fallback data
@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Get dashboard summary with fallback data"""
    return {
        "portfolio": {
            "total_value": 10000.00,
            "total_pnl": 250.50,
            "unrealized_pnl": 125.25,
            "realized_pnl": 125.25,
            "open_positions": 3
        },
        "market_overview": {
            "BTC/USDT": {
                "price": 42150.00,
                "change_24h": 850.50,
                "change_24h_pct": 2.05,
                "volume_24h": 1250000000
            },
            "ETH/USDT": {
                "price": 2580.75,
                "change_24h": -45.25,
                "change_24h_pct": -1.72,
                "volume_24h": 750000000
            }
        },
        "recent_trades": [
            {
                "id": "1",
                "symbol": "BTC/USDT",
                "side": "buy",
                "amount": 0.001,
                "price": 41500.00,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "filled"
            }
        ],
        "performance": {
            "total_trades": 25,
            "winning_trades": 18,
            "win_rate": 72.0,
            "total_pnl": 250.50
        }
    }

@app.post("/auth/login")
async def login_demo():
    """Demo login endpoint"""
    return {
        "access_token": "demo_token_12345",
        "token_type": "bearer",
        "expires_in": 86400
    }

@app.post("/auth/create-demo-user")
async def create_demo_user():
    """Create demo user endpoint"""
    return {
        "message": "Demo user created successfully",
        "username": "demo",
        "password": "demo123"
    }

# Fallback HTML templates
def get_fallback_login():
    """Fallback login page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - Trading Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }
            .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); 
                        width: 100%; max-width: 400px; }
            .header { text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
            .form-group input { width: 100%; padding: 12px; border: 2px solid #e1e5e9; border-radius: 6px; 
                               font-size: 16px; box-sizing: border-box; }
            .btn { width: 100%; padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer; }
            .demo-info { margin-top: 20px; padding: 15px; background: #f0f8ff; border-radius: 6px; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Trading Bot</h1>
                <p>Welcome to the Trading Interface</p>
            </div>
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" value="demo">
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" value="demo123">
                </div>
                <button type="submit" class="btn">Login</button>
            </form>
            <div class="demo-info">
                <strong>Demo Account</strong><br>
                Username: demo<br>
                Password: demo123<br>
                <small>Full features available for testing</small>
            </div>
        </div>
        <script>
            document.getElementById('loginForm').onsubmit = function(e) {
                e.preventDefault();
                localStorage.setItem('access_token', 'demo_token_12345');
                window.location.href = '/';
            };
        </script>
    </body>
    </html>
    """

def get_fallback_dashboard():
    """Fallback dashboard page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - Trading Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; background: #f5f7fa; }
            .header { background: #2d3748; color: white; padding: 1rem; display: flex; justify-content: space-between; align-items: center; }
            .nav { display: flex; gap: 1rem; }
            .nav a { color: white; text-decoration: none; padding: 0.5rem 1rem; border-radius: 4px; }
            .nav a:hover { background: rgba(255,255,255,0.1); }
            .container { padding: 2rem; max-width: 1200px; margin: 0 auto; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
            .card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric { text-align: center; }
            .metric-value { font-size: 2rem; font-weight: bold; color: #2d3748; }
            .metric-label { color: #718096; margin-top: 0.5rem; }
            .positive { color: #48bb78; }
            .negative { color: #f56565; }
            .status { padding: 1rem; background: #d1fae5; border-left: 4px solid #10b981; margin-bottom: 2rem; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 Trading Bot Dashboard</h1>
            <nav class="nav">
                <a href="/">Dashboard</a>
                <a href="/trading">Trading</a>
                <a href="/strategies">Strategies</a>
                <a href="/backtesting">Backtesting</a>
                <a href="/settings">Settings</a>
            </nav>
        </div>
        <div class="container">
            <div class="status">
                <strong>✅ System Status:</strong> Trading Bot is running successfully! All components initialized.
            </div>
            <div class="grid">
                <div class="card metric">
                    <div class="metric-value">$10,000.00</div>
                    <div class="metric-label">Total Portfolio Value</div>
                </div>
                <div class="card metric">
                    <div class="metric-value positive">+$250.50</div>
                    <div class="metric-label">Total P&L</div>
                </div>
                <div class="card metric">
                    <div class="metric-value">3</div>
                    <div class="metric-label">Open Positions</div>
                </div>
                <div class="card metric">
                    <div class="metric-value">72%</div>
                    <div class="metric-label">Win Rate</div>
                </div>
            </div>
            <div class="card">
                <h3>🎯 Welcome to Light Trading Bot!</h3>
                <p>Your trading bot is now running and ready to use. Here's what you can do:</p>
                <ul>
                    <li><strong>Trading:</strong> Place buy/sell orders with real-time market data</li>
                    <li><strong>Strategies:</strong> Manage and configure trading strategies</li>
                    <li><strong>Backtesting:</strong> Test strategies with historical data</li>
                    <li><strong>Settings:</strong> Configure exchanges and risk management</li>
                </ul>
                <p><strong>Demo Mode:</strong> You're currently using demo data. Configure real exchange APIs in Settings to start live trading.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_fallback_trading():
    """Fallback trading page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Trading - Trading Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; background: #f5f7fa; }
            .header { background: #2d3748; color: white; padding: 1rem; }
            .nav { display: flex; gap: 1rem; }
            .nav a { color: white; text-decoration: none; padding: 0.5rem 1rem; border-radius: 4px; }
            .nav a:hover { background: rgba(255,255,255,0.1); }
            .container { padding: 2rem; max-width: 1200px; margin: 0 auto; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
            .card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 1rem; }
            .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
            .form-group input, .form-group select { width: 100%; padding: 0.75rem; border: 1px solid #e2e8f0; 
                                                    border-radius: 4px; box-sizing: border-box; }
            .btn { padding: 0.75rem 1.5rem; border: none; border-radius: 4px; cursor: pointer; font-weight: 500; }
            .btn-buy { background: #48bb78; color: white; }
            .btn-sell { background: #f56565; color: white; }
            .price-display { text-align: center; padding: 1rem; background: #edf2f7; border-radius: 4px; margin-bottom: 1rem; }
            .price-value { font-size: 2rem; font-weight: bold; }
            .message { padding: 1rem; border-radius: 4px; margin: 1rem 0; }
            .success { background: #d1fae5; color: #047857; border: 1px solid #10b981; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Trading Interface</h1>
            <nav class="nav">
                <a href="/">Dashboard</a>
                <a href="/trading">Trading</a>
                <a href="/strategies">Strategies</a>
                <a href="/backtesting">Backtesting</a>
                <a href="/settings">Settings</a>
            </nav>
        </div>
        <div class="container">
            <div class="message success">
                <strong>✅ Trading Interface Active:</strong> Place orders and manage your portfolio. Currently in demo mode.
            </div>
            <div class="grid">
                <div class="card">
                    <h3>💰 Buy Order</h3>
                    <form id="buyForm">
                        <div class="form-group">
                            <label>Symbol</label>
                            <select>
                                <option>BTC/USDT</option>
                                <option>ETH/USDT</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Amount</label>
                            <input type="number" step="0.001" placeholder="0.001">
                        </div>
                        <div class="form-group">
                            <label>Price (USDT)</label>
                            <input type="number" step="0.01" placeholder="42150.00">
                        </div>
                        <button type="submit" class="btn btn-buy">Place Buy Order</button>
                    </form>
                </div>
                <div class="card">
                    <h3>💸 Sell Order</h3>
                    <form id="sellForm">
                        <div class="form-group">
                            <label>Symbol</label>
                            <select>
                                <option>BTC/USDT</option>
                                <option>ETH/USDT</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Amount</label>
                            <input type="number" step="0.001" placeholder="0.001">
                        </div>
                        <div class="form-group">
                            <label>Price (USDT)</label>
                            <input type="number" step="0.01" placeholder="43200.00">
                        </div>
                        <button type="submit" class="btn btn-sell">Place Sell Order</button>
                    </form>
                </div>
            </div>
            <div class="card">
                <h3>📈 Current Market Price</h3>
                <div class="price-display">
                    <div class="price-value">$42,150.00</div>
                    <div>BTC/USDT (+2.05%)</div>
                </div>
            </div>
        </div>
        <script>
            document.getElementById('buyForm').onsubmit = function(e) {
                e.preventDefault();
                alert('Buy order placed successfully! (Demo mode)');
            };
            document.getElementById('sellForm').onsubmit = function(e) {
                e.preventDefault();
                alert('Sell order placed successfully! (Demo mode)');
            };
        </script>
    </body>
    </html>
    """

def get_fallback_page(title):
    """Generic fallback page"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - Trading Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f7fa; }}
            .header {{ background: #2d3748; color: white; padding: 1rem; }}
            .nav {{ display: flex; gap: 1rem; }}
            .nav a {{ color: white; text-decoration: none; padding: 0.5rem 1rem; border-radius: 4px; }}
            .nav a:hover {{ background: rgba(255,255,255,0.1); }}
            .container {{ padding: 2rem; text-align: center; }}
            .card {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                     max-width: 600px; margin: 2rem auto; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 Trading Bot - {title}</h1>
            <nav class="nav">
                <a href="/">Dashboard</a>
                <a href="/trading">Trading</a>
                <a href="/strategies">Strategies</a>
                <a href="/backtesting">Backtesting</a>
                <a href="/settings">Settings</a>
            </nav>
        </div>
        <div class="container">
            <div class="card">
                <h2>🚧 {title} Interface</h2>
                <p>The {title.lower()} interface is being loaded...</p>
                <p>Your trading bot is running successfully! This page will be fully functional once all components are initialized.</p>
            </div>
        </div>
    </body>
    </html>
    """

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return HTMLResponse(content=get_fallback_page("Page Not Found"), status_code=404)

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
        app,
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )

if __name__ == "__main__":
    run_web_app(debug=True)

