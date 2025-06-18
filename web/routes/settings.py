# web/routes/settings.py

"""
Settings Routes
Account settings, exchange configuration, notification preferences
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from cryptography.fernet import Fernet
import logging
import json

from web.auth import require_auth, generate_csrf_token, auth_manager
from database.models.users import User
from database.repositories import (
    ExchangeRepository, ConfigurationRepository, 
    NotificationRepository, TelegramConfigRepository
)
from core.config_manager import ConfigManager
from api_clients.manager import APIClientManager

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

# Repositories and services
exchange_repo = ExchangeRepository()
config_repo = ConfigurationRepository()
notification_repo = NotificationRepository()
telegram_repo = TelegramConfigRepository()
config = ConfigManager()
api_manager = APIClientManager()

# Pydantic models
class ExchangeConfigRequest(BaseModel):
    exchange_name: str
    display_name: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    testnet: bool = False
    
    @validator('exchange_name')
    def validate_exchange(cls, v):
        allowed = ['kucoin', 'binance', 'okx', 'bybit']
        if v not in allowed:
            raise ValueError(f'Exchange must be one of: {", ".join(allowed)}')
        return v

class NotificationSettingsRequest(BaseModel):
    channels: List[str]
    trade_signals: bool = True
    execution_confirmations: bool = True
    backtest_results: bool = True
    system_alerts: bool = True
    portfolio_updates: bool = False

class TelegramConfigRequest(BaseModel):
    config_name: str
    bot_token: str
    channels: List[str] = []
    users: List[str] = []
    permissions: List[str] = []
    notification_types: List[str] = []

@router.get("/")
async def settings_page(
    request: Request,
    user: User = Depends(require_auth)
):
    """Main settings page"""
    try:
        # Get user exchanges
        exchanges = await exchange_repo.get_user_exchanges(user.id)
        
        # Get user configurations
        user_configs = await config_repo.get_user_configurations(user.id)
        
        # Get notification settings
        notification_settings = await get_notification_settings(user.id)
        
        # Get telegram configurations
        telegram_configs = await telegram_repo.get_user_configs(user.id)
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("settings/index.html", {
            "request": request,
            "user": user,
            "exchanges": exchanges,
            "user_configs": user_configs,
            "notification_settings": notification_settings,
            "telegram_configs": telegram_configs,
            "csrf_token": csrf_token,
            "page_title": "Settings"
        })
        
    except Exception as e:
        logger.error(f"Settings page error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load settings")

@router.get("/exchanges")
async def exchanges_page(
    request: Request,
    user: User = Depends(require_auth)
):
    """Exchange configuration page"""
    try:
        # Get user exchanges
        exchanges = await exchange_repo.get_user_exchanges(user.id)
        
        # Get supported exchanges
        supported_exchanges = config.get("trading.supported_exchanges", [])
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("settings/exchanges.html", {
            "request": request,
            "user": user,
            "exchanges": exchanges,
            "supported_exchanges": supported_exchanges,
            "csrf_token": csrf_token,
            "page_title": "Exchange Configuration"
        })
        
    except Exception as e:
        logger.error(f"Exchanges page error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load exchange settings")

@router.get("/notifications")
async def notifications_page(
    request: Request,
    user: User = Depends(require_auth)
):
    """Notification settings page"""
    try:
        # Get notification settings
        notification_settings = await get_notification_settings(user.id)
        
        # Get recent notifications
        recent_notifications = await notification_repo.get_recent_notifications(user.id, limit=20)
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("settings/notifications.html", {
            "request": request,
            "user": user,
            "notification_settings": notification_settings,
            "recent_notifications": recent_notifications,
            "csrf_token": csrf_token,
            "page_title": "Notification Settings"
        })
        
    except Exception as e:
        logger.error(f"Notifications page error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load notification settings")

@router.get("/telegram")
async def telegram_page(
    request: Request,
    user: User = Depends(require_auth)
):
    """Telegram configuration page"""
    try:
        # Get telegram configurations
        telegram_configs = await telegram_repo.get_user_configs(user.id)
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("settings/telegram.html", {
            "request": request,
            "user": user,
            "telegram_configs": telegram_configs,
            "csrf_token": csrf_token,
            "page_title": "Telegram Configuration"
        })
        
    except Exception as e:
        logger.error(f"Telegram page error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load telegram settings")

@router.post("/exchange/add")
async def add_exchange(
    request: Request,
    exchange_name: str = Form(...),
    display_name: str = Form(...),
    api_key: str = Form(...),
    api_secret: str = Form(...),
    passphrase: str = Form(""),
    testnet: bool = Form(False),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Add new exchange configuration"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Validate exchange request
        exchange_request = ExchangeConfigRequest(
            exchange_name=exchange_name,
            display_name=display_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase if passphrase else None,
            testnet=testnet
        )
        
        # Test connection before saving
        test_result = await test_exchange_connection(exchange_request)
        if not test_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Connection test failed: {test_result['error']}"
            )
        
        # Encrypt API credentials
        cipher = Fernet(config.get("security.encryption_key").encode())
        encrypted_api_key = cipher.encrypt(api_key.encode()).decode()
        encrypted_api_secret = cipher.encrypt(api_secret.encode()).decode()
        encrypted_passphrase = None
        if passphrase:
            encrypted_passphrase = cipher.encrypt(passphrase.encode()).decode()
        
        # Save exchange configuration
        exchange = await exchange_repo.create({
            "user_id": user.id,
            "exchange_name": exchange_name,
            "display_name": display_name,
            "api_key_encrypted": encrypted_api_key,
            "api_secret_encrypted": encrypted_api_secret,
            "passphrase_encrypted": encrypted_passphrase,
            "testnet": testnet,
            "active": True
        })
        
        return RedirectResponse(
            url="/settings/exchanges?success=Exchange added successfully",
            status_code=302
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Add exchange error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add exchange")

@router.post("/exchange/update/{exchange_id}")
async def update_exchange(
    request: Request,
    exchange_id: str,
    display_name: str = Form(...),
    api_key: str = Form(""),
    api_secret: str = Form(""),
    passphrase: str = Form(""),
    testnet: bool = Form(False),
    active: bool = Form(True),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Update exchange configuration"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Get existing exchange
        exchange = await exchange_repo.get_by_id(exchange_id)
        if not exchange or str(exchange.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        # Prepare update data
        update_data = {
            "display_name": display_name,
            "testnet": testnet,
            "active": active
        }
        
        # Update API credentials if provided
        if api_key and api_secret:
            # Test new credentials
            test_request = ExchangeConfigRequest(
                exchange_name=exchange.exchange_name,
                display_name=display_name,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase if passphrase else None,
                testnet=testnet
            )
            
            test_result = await test_exchange_connection(test_request)
            if not test_result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Connection test failed: {test_result['error']}"
                )
            
            # Encrypt new credentials
            cipher = Fernet(config.get("security.encryption_key").encode())
            update_data["api_key_encrypted"] = cipher.encrypt(api_key.encode()).decode()
            update_data["api_secret_encrypted"] = cipher.encrypt(api_secret.encode()).decode()
            
            if passphrase:
                update_data["passphrase_encrypted"] = cipher.encrypt(passphrase.encode()).decode()
        
        # Update exchange
        await exchange_repo.update(exchange_id, update_data)
        
        return RedirectResponse(
            url="/settings/exchanges?success=Exchange updated successfully",
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update exchange error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update exchange")

@router.post("/exchange/delete/{exchange_id}")
async def delete_exchange(
    request: Request,
    exchange_id: str,
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Delete exchange configuration"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Get exchange
        exchange = await exchange_repo.get_by_id(exchange_id)
        if not exchange or str(exchange.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        # Delete exchange
        await exchange_repo.delete(exchange_id)
        
        return RedirectResponse(
            url="/settings/exchanges?success=Exchange deleted successfully",
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete exchange error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete exchange")

@router.post("/notifications/update")
async def update_notification_settings(
    request: Request,
    channels: List[str] = Form([]),
    trade_signals: bool = Form(False),
    execution_confirmations: bool = Form(False),
    backtest_results: bool = Form(False),
    system_alerts: bool = Form(False),
    portfolio_updates: bool = Form(False),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Update notification settings"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Prepare notification settings
        settings = {
            "channels": channels,
            "trade_signals": trade_signals,
            "execution_confirmations": execution_confirmations,
            "backtest_results": backtest_results,
            "system_alerts": system_alerts,
            "portfolio_updates": portfolio_updates
        }
        
        # Save notification settings
        await config_repo.set_user_config(
            user.id, "notifications", "preferences", settings
        )
        
        return RedirectResponse(
            url="/settings/notifications?success=Notification settings updated",
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"Update notification settings error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification settings")

@router.post("/telegram/add")
async def add_telegram_config(
    request: Request,
    config_name: str = Form(...),
    bot_token: str = Form(...),
    channels: str = Form(""),
    users: str = Form(""),
    permissions: List[str] = Form([]),
    notification_types: List[str] = Form([]),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Add telegram configuration"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Parse channels and users
        channels_list = [c.strip() for c in channels.split(',') if c.strip()]
        users_list = [u.strip() for u in users.split(',') if u.strip()]
        
        # Test bot token
        test_result = await test_telegram_bot(bot_token)
        if not test_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Bot token test failed: {test_result['error']}"
            )
        
        # Encrypt bot token
        cipher = Fernet(config.get("security.encryption_key").encode())
        encrypted_token = cipher.encrypt(bot_token.encode()).decode()
        
        # Create telegram configuration
        await telegram_repo.create({
            "user_id": user.id,
            "config_name": config_name,
            "bot_token_encrypted": encrypted_token,
            "channels": channels_list,
            "users": users_list,
            "permissions": permissions,
            "notification_types": notification_types,
            "active": True
        })
        
        return RedirectResponse(
            url="/settings/telegram?success=Telegram configuration added",
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add telegram config error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add telegram configuration")

# API endpoints
@router.get("/api/exchange/test")
async def api_test_exchange(
    exchange: str,
    api_key: str,
    api_secret: str,
    passphrase: Optional[str] = None,
    testnet: bool = False
):
    """Test exchange connection"""
    try:
        request = ExchangeConfigRequest(
            exchange_name=exchange,
            display_name="Test",
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            testnet=testnet
        )
        
        result = await test_exchange_connection(request)
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"API test exchange error: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        })

@router.get("/api/telegram/test")
async def api_test_telegram(bot_token: str):
    """Test telegram bot token"""
    try:
        result = await test_telegram_bot(bot_token)
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"API test telegram error: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        })

@router.get("/api/notifications/history")
async def api_notification_history(
    user: User = Depends(require_auth),
    limit: int = Query(50, ge=1, le=1000),
    type: Optional[str] = Query(None)
):
    """Get notification history"""
    try:
        filters = {"limit": limit}
        if type:
            filters["type"] = type
        
        notifications = await notification_repo.get_user_notifications(user.id, filters)
        
        return JSONResponse(content=[
            {
                "id": str(notif.id),
                "type": notif.type,
                "title": notif.title,
                "message": notif.message,
                "timestamp": notif.sent_at.isoformat() if notif.sent_at else None,
                "read": notif.read
            }
            for notif in notifications
        ])
        
    except Exception as e:
        logger.error(f"Notification history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notification history")

# Helper functions
async def get_notification_settings(user_id: str) -> Dict[str, Any]:
    """Get user notification settings"""
    try:
        settings = await config_repo.get_user_config(user_id, "notifications", "preferences")
        
        if not settings:
            # Default settings
            settings = {
                "channels": ["web"],
                "trade_signals": True,
                "execution_confirmations": True,
                "backtest_results": True,
                "system_alerts": True,
                "portfolio_updates": False
            }
        
        return settings
        
    except Exception as e:
        logger.error(f"Get notification settings error: {e}")
        return {}

async def test_exchange_connection(request: ExchangeConfigRequest) -> Dict[str, Any]:
    """Test exchange API connection"""
    try:
        # Test connection via ccxt client
        balance = await api_manager.ccxt_client.get_balance(
            request.exchange_name,
            request.api_key,
            request.api_secret,
            request.passphrase
        )
        
        if balance:
            return {
                "success": True,
                "message": "Connection successful",
                "balance_info": {
                    "total_currencies": len(balance.get("total", {})),
                    "has_funds": any(v > 0 for v in balance.get("total", {}).values())
                }
            }
        else:
            return {
                "success": False,
                "error": "No balance data received"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def test_telegram_bot(bot_token: str) -> Dict[str, Any]:
    """Test telegram bot token"""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        bot_info = data.get("result", {})
                        return {
                            "success": True,
                            "message": "Bot token is valid",
                            "bot_info": {
                                "username": bot_info.get("username"),
                                "first_name": bot_info.get("first_name"),
                                "can_join_groups": bot_info.get("can_join_groups", False),
                                "can_read_all_group_messages": bot_info.get("can_read_all_group_messages", False)
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("description", "Invalid bot token")
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}"
                    }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
