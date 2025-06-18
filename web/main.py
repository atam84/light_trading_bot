# web/main.py

"""
FastAPI Web Application Main
Mobile-responsive trading bot dashboard with real-time features
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import os
from typing import Optional
import logging
from datetime import datetime

# Internal imports
from web.routes import auth, dashboard, trading, strategies, backtesting, settings, api
from web.websocket import websocket_manager
from web.auth import get_current_user, verify_token
from core.config_manager import ConfigManager
from core.logging_manager import LoggingManager

# Initialize logging
logger = LoggingManager().get_logger(__name__)

# Security
security = HTTPBearer()

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Load configuration
    config = ConfigManager()
    
    # Create FastAPI app
    app = FastAPI(
        title="Trading Bot Dashboard",
        description="Comprehensive trading bot web interface",
        version="1.0.0",
        docs_url="/docs" if config.get("web.debug_mode", False) else None,
        redoc_url="/redoc" if config.get("web.debug_mode", False) else None
    )
    
    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("web.cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.get("security.secret_key"),
        max_age=config.get("web.session_timeout", 3600)
    )
    
    # Static files
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
    
    # Templates
    templates = Jinja2Templates(directory="web/templates")
    
    # Add global template variables
    @app.middleware("http")
    async def add_template_globals(request: Request, call_next):
        """Add global variables to all templates"""
        request.state.config = config
        request.state.current_time = datetime.now()
        response = await call_next(request)
        return response
    
    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(dashboard.router, prefix="", tags=["Dashboard"])
    app.include_router(trading.router, prefix="/trading", tags=["Trading"])
    app.include_router(strategies.router, prefix="/strategies", tags=["Strategies"])
    app.include_router(backtesting.router, prefix="/backtesting", tags=["Backtesting"])
    app.include_router(settings.router, prefix="/settings", tags=["Settings"])
    app.include_router(api.router, prefix="/api/v1", tags=["API"])
    
    # WebSocket
    app.include_router(websocket_manager.router, prefix="/ws", tags=["WebSocket"])
    
    # Root redirect
    @app.get("/")
    async def root(request: Request):
        """Redirect to dashboard or login"""
        user = await get_current_user(request)
        if user:
            return templates.TemplateResponse("dashboard/index.html", {
                "request": request,
                "user": user,
                "page_title": "Dashboard"
            })
        else:
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "page_title": "Login"
            })
    
    # Health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    
    # Error handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        if exc.status_code == 401:
            return templates.TemplateResponse("auth/login.html", {
                "request": request,
                "error": "Authentication required",
                "page_title": "Login"
            }, status_code=401)
        
        return templates.TemplateResponse("errors/error.html", {
            "request": request,
            "error_code": exc.status_code,
            "error_message": exc.detail,
            "page_title": f"Error {exc.status_code}"
        }, status_code=exc.status_code)
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return templates.TemplateResponse("errors/error.html", {
            "request": request,
            "error_code": 500,
            "error_message": "Internal server error",
            "page_title": "Error 500"
        }, status_code=500)
    
    return app

def run_web_server():
    """Run the web server"""
    config = ConfigManager()
    
    host = config.get("web.host", "0.0.0.0")
    port = config.get("web.port", 5000)
    debug = config.get("web.debug_mode", False)
    
    logger.info(f"Starting web server on {host}:{port}")
    
    uvicorn.run(
        "web.main:create_app",
        factory=True,
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )

# Create app instance
app = create_app()

if __name__ == "__main__":
    run_web_server()
