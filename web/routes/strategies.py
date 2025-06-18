# web/routes/strategies.py

"""
Strategy Management Routes
Strategy builder, marketplace, import/export functionality
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
import json
import logging
from datetime import datetime

from web.auth import require_auth, generate_csrf_token
from database.models.users import User
from database.repositories import StrategyRepository, StrategyMarketplaceRepository
from strategies.manager import StrategyManager
from strategies.factory import StrategyFactory
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

# Repositories and services
strategy_repo = StrategyRepository()
marketplace_repo = StrategyMarketplaceRepository()
strategy_manager = StrategyManager()
strategy_factory = StrategyFactory()
config = ConfigManager()

# Pydantic models
class StrategyCreateRequest(BaseModel):
    name: str
    description: str
    strategy_type: str
    config: Dict[str, Any]
    public: bool = False
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Strategy name must be at least 3 characters')
        return v.strip()
    
    @validator('strategy_type')
    def validate_type(cls, v):
        allowed_types = ['simple', 'grid', 'indicator', 'dca', 'volatility_breakout']
        if v not in allowed_types:
            raise ValueError(f'Strategy type must be one of: {", ".join(allowed_types)}')
        return v

class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
    public: Optional[bool] = None

@router.get("/")
async def strategies_page(
    request: Request,
    user: User = Depends(require_auth)
):
    """Main strategies page"""
    try:
        # Get user strategies
        user_strategies = await strategy_repo.get_user_strategies(user.id)
        
        # Get strategy templates
        templates_data = strategy_factory.get_available_templates()
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("strategies/index.html", {
            "request": request,
            "user": user,
            "strategies": user_strategies,
            "templates": templates_data,
            "csrf_token": csrf_token,
            "page_title": "Strategies"
        })
        
    except Exception as e:
        logger.error(f"Strategies page error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load strategies")

@router.get("/builder")
async def strategy_builder(
    request: Request,
    user: User = Depends(require_auth),
    template: Optional[str] = Query(None)
):
    """Strategy builder interface"""
    try:
        # Get strategy template if specified
        template_config = None
        if template:
            template_config = strategy_factory.get_template(template)
        
        # Get available indicators
        available_indicators = strategy_factory.get_available_indicators()
        
        # Get supported timeframes
        supported_timeframes = config.get("trading.supported_timeframes", [])
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("strategies/builder.html", {
            "request": request,
            "user": user,
            "template_config": template_config,
            "template_name": template,
            "available_indicators": available_indicators,
            "supported_timeframes": supported_timeframes,
            "csrf_token": csrf_token,
            "page_title": "Strategy Builder"
        })
        
    except Exception as e:
        logger.error(f"Strategy builder error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load strategy builder")

@router.get("/edit/{strategy_id}")
async def edit_strategy(
    request: Request,
    strategy_id: str,
    user: User = Depends(require_auth)
):
    """Edit existing strategy"""
    try:
        # Get strategy
        strategy = await strategy_repo.get_by_id(strategy_id)
        if not strategy or str(strategy.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get available indicators
        available_indicators = strategy_factory.get_available_indicators()
        
        # Get supported timeframes
        supported_timeframes = config.get("trading.supported_timeframes", [])
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("strategies/edit.html", {
            "request": request,
            "user": user,
            "strategy": strategy,
            "available_indicators": available_indicators,
            "supported_timeframes": supported_timeframes,
            "csrf_token": csrf_token,
            "page_title": f"Edit {strategy.name}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Edit strategy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load strategy editor")

@router.get("/marketplace")
async def marketplace_page(
    request: Request,
    user: User = Depends(require_auth),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Strategy marketplace"""
    try:
        # Get public strategies
        filters = {}
        if category:
            filters["category"] = category
        if search:
            filters["search"] = search
        
        public_strategies = await marketplace_repo.get_public_strategies(filters)
        
        # Get categories
        categories = await marketplace_repo.get_categories()
        
        return templates.TemplateResponse("strategies/marketplace.html", {
            "request": request,
            "user": user,
            "strategies": public_strategies,
            "categories": categories,
            "current_category": category,
            "search_query": search,
            "page_title": "Strategy Marketplace"
        })
        
    except Exception as e:
        logger.error(f"Marketplace error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load marketplace")

@router.post("/create")
async def create_strategy(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    strategy_type: str = Form(...),
    config_json: str = Form(...),
    public: bool = Form(False),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Create new strategy"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Parse configuration
        try:
            config_data = json.loads(config_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid configuration JSON")
        
        # Validate strategy request
        strategy_request = StrategyCreateRequest(
            name=name,
            description=description,
            strategy_type=strategy_type,
            config=config_data,
            public=public
        )
        
        # Validate strategy configuration
        validation_result = strategy_factory.validate_strategy_config(
            strategy_type, config_data
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy configuration: {validation_result['errors']}"
            )
        
        # Create strategy
        strategy = await strategy_repo.create({
            "user_id": user.id,
            "name": strategy_request.name,
            "description": strategy_request.description,
            "strategy_type": strategy_request.strategy_type,
            "config": strategy_request.config,
            "public": strategy_request.public,
            "active": False
        })
        
        # Add to marketplace if public
        if strategy_request.public:
            await marketplace_repo.add_to_marketplace(strategy.id, {
                "title": strategy_request.name,
                "description": strategy_request.description,
                "category": strategy_request.strategy_type,
                "tags": [strategy_request.strategy_type],
                "author_id": user.id
            })
        
        return RedirectResponse(
            url="/strategies?success=Strategy created successfully",
            status_code=302
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Create strategy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create strategy")

@router.post("/update/{strategy_id}")
async def update_strategy(
    request: Request,
    strategy_id: str,
    name: str = Form(...),
    description: str = Form(...),
    config_json: str = Form(...),
    active: bool = Form(False),
    public: bool = Form(False),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Update existing strategy"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Get strategy
        strategy = await strategy_repo.get_by_id(strategy_id)
        if not strategy or str(strategy.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Parse configuration
        try:
            config_data = json.loads(config_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid configuration JSON")
        
        # Validate configuration
        validation_result = strategy_factory.validate_strategy_config(
            strategy.strategy_type, config_data
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy configuration: {validation_result['errors']}"
            )
        
        # Update strategy
        await strategy_repo.update(strategy_id, {
            "name": name,
            "description": description,
            "config": config_data,
            "active": active,
            "public": public,
            "updated_at": datetime.utcnow()
        })
        
        return RedirectResponse(
            url="/strategies?success=Strategy updated successfully",
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update strategy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update strategy")

@router.post("/delete/{strategy_id}")
async def delete_strategy(
    request: Request,
    strategy_id: str,
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Delete strategy"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Get strategy
        strategy = await strategy_repo.get_by_id(strategy_id)
        if not strategy or str(strategy.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Check if strategy is active
        if strategy.active:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete active strategy. Deactivate it first."
            )
        
        # Delete from marketplace if public
        if strategy.public:
            await marketplace_repo.remove_from_marketplace(strategy_id)
        
        # Delete strategy
        await strategy_repo.delete(strategy_id)
        
        return RedirectResponse(
            url="/strategies?success=Strategy deleted successfully",
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete strategy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete strategy")

@router.post("/toggle/{strategy_id}")
async def toggle_strategy(
    strategy_id: str,
    user: User = Depends(require_auth)
):
    """Toggle strategy active status"""
    try:
        # Get strategy
        strategy = await strategy_repo.get_by_id(strategy_id)
        if not strategy or str(strategy.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Toggle active status
        new_status = not strategy.active
        await strategy_repo.update(strategy_id, {"active": new_status})
        
        # Update strategy manager
        if new_status:
            await strategy_manager.activate_strategy(strategy_id)
        else:
            await strategy_manager.deactivate_strategy(strategy_id)
        
        return JSONResponse(content={
            "success": True,
            "active": new_status,
            "message": f"Strategy {'activated' if new_status else 'deactivated'}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Toggle strategy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle strategy")

@router.get("/export/{strategy_id}")
async def export_strategy(
    strategy_id: str,
    user: User = Depends(require_auth)
):
    """Export strategy as JSON"""
    try:
        # Get strategy
        strategy = await strategy_repo.get_by_id(strategy_id)
        if not strategy or str(strategy.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Prepare export data
        export_data = {
            "name": strategy.name,
            "description": strategy.description,
            "strategy_type": strategy.strategy_type,
            "config": strategy.config,
            "exported_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        # Return as JSON download
        filename = f"{strategy.name.replace(' ', '_').lower()}_strategy.json"
        content = json.dumps(export_data, indent=2)
        
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export strategy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to export strategy")

@router.post("/import")
async def import_strategy(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Import strategy from JSON file"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Validate file type
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are allowed")
        
        # Read file content
        content = await file.read()
        
        try:
            strategy_data = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        
        # Validate required fields
        required_fields = ["name", "strategy_type", "config"]
        for field in required_fields:
            if field not in strategy_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Validate strategy configuration
        validation_result = strategy_factory.validate_strategy_config(
            strategy_data["strategy_type"], strategy_data["config"]
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy configuration: {validation_result['errors']}"
            )
        
        # Create imported strategy
        imported_name = f"{strategy_data['name']} (Imported)"
        strategy = await strategy_repo.create({
            "user_id": user.id,
            "name": imported_name,
            "description": strategy_data.get("description", "Imported strategy"),
            "strategy_type": strategy_data["strategy_type"],
            "config": strategy_data["config"],
            "public": False,
            "active": False
        })
        
        return RedirectResponse(
            url="/strategies?success=Strategy imported successfully",
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import strategy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to import strategy")

@router.post("/marketplace/import/{marketplace_id}")
async def import_from_marketplace(
    marketplace_id: str,
    user: User = Depends(require_auth)
):
    """Import strategy from marketplace"""
    try:
        # Get marketplace strategy
        marketplace_strategy = await marketplace_repo.get_by_id(marketplace_id)
        if not marketplace_strategy:
            raise HTTPException(status_code=404, detail="Strategy not found in marketplace")
        
        # Get original strategy
        original_strategy = await strategy_repo.get_by_id(marketplace_strategy.strategy_id)
        if not original_strategy:
            raise HTTPException(status_code=404, detail="Original strategy not found")
        
        # Create copy for user
        imported_name = f"{original_strategy.name} (From Marketplace)"
        strategy = await strategy_repo.create({
            "user_id": user.id,
            "name": imported_name,
            "description": original_strategy.description,
            "strategy_type": original_strategy.strategy_type,
            "config": original_strategy.config,
            "public": False,
            "active": False
        })
        
        # Update download count
        await marketplace_repo.increment_downloads(marketplace_id)
        
        return JSONResponse(content={
            "success": True,
            "message": "Strategy imported successfully",
            "strategy_id": str(strategy.id)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import from marketplace error: {e}")
        raise HTTPException(status_code=500, detail="Failed to import strategy")

# API endpoints
@router.get("/api/templates")
async def api_get_templates():
    """Get available strategy templates"""
    try:
        templates = strategy_factory.get_available_templates()
        return JSONResponse(content=templates)
        
    except Exception as e:
        logger.error(f"Get templates error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get templates")

@router.get("/api/template/{template_name}")
async def api_get_template(template_name: str):
    """Get specific template configuration"""
    try:
        template = strategy_factory.get_template(template_name)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return JSONResponse(content=template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get template error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get template")

@router.post("/api/validate")
async def api_validate_strategy(
    strategy_type: str,
    config: Dict[str, Any]
):
    """Validate strategy configuration"""
    try:
        result = strategy_factory.validate_strategy_config(strategy_type, config)
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Validate strategy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate strategy")
