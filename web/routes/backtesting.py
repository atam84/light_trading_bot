# web/routes/backtesting.py

"""
Backtesting Routes
Run backtests, view results, performance analysis, and strategy comparison
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import asyncio
import logging

from web.auth import require_auth, generate_csrf_token
from database.models.users import User
from database.repositories import BacktestRepository, StrategyRepository
from core.backtesting_engine import BacktestingEngine
from core.config_manager import ConfigManager
from api_clients.manager import APIClientManager

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

# Repositories and services
backtest_repo = BacktestRepository()
strategy_repo = StrategyRepository()
config = ConfigManager()
api_manager = APIClientManager()

# Pydantic models
class BacktestRequest(BaseModel):
    strategy_id: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_balance: float = 10000.0
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        allowed = ['1m', '5m', '15m', '30m', '1h', '4h', '8h', '1d', '1w']
        if v not in allowed:
            raise ValueError(f'Timeframe must be one of: {", ".join(allowed)}')
        return v
    
    @validator('initial_balance')
    def validate_balance(cls, v):
        if v <= 0:
            raise ValueError('Initial balance must be positive')
        return v

# Background task storage (in production, use Redis or similar)
running_backtests = {}

@router.get("/")
async def backtesting_page(
    request: Request,
    user: User = Depends(require_auth)
):
    """Main backtesting page"""
    try:
        # Get user strategies
        user_strategies = await strategy_repo.get_user_strategies(user.id)
        
        # Get recent backtest results
        recent_backtests = await backtest_repo.get_user_backtests(user.id, limit=10)
        
        # Get supported symbols and timeframes
        supported_symbols = config.get("backtesting.supported_symbols", ["BTC/USDT", "ETH/USDT"])
        supported_timeframes = config.get("trading.supported_timeframes", [])
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
        
        return templates.TemplateResponse("backtesting/index.html", {
            "request": request,
            "user": user,
            "strategies": user_strategies,
            "recent_backtests": recent_backtests,
            "supported_symbols": supported_symbols,
            "supported_timeframes": supported_timeframes,
            "csrf_token": csrf_token,
            "page_title": "Backtesting"
        })
        
    except Exception as e:
        logger.error(f"Backtesting page error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load backtesting page")

@router.get("/results")
async def backtest_results_page(
    request: Request,
    user: User = Depends(require_auth),
    strategy_id: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None)
):
    """Backtest results page with filtering"""
    try:
        # Build filters
        filters = {}
        if strategy_id:
            filters["strategy_id"] = strategy_id
        if symbol:
            filters["symbol"] = symbol
        
        # Get backtest results
        backtests = await backtest_repo.get_user_backtests(user.id, filters)
        
        # Get user strategies for filter dropdown
        user_strategies = await strategy_repo.get_user_strategies(user.id)
        
        # Get unique symbols from backtests
        all_backtests = await backtest_repo.get_user_backtests(user.id)
        unique_symbols = list(set(b.symbol for b in all_backtests if b.symbol))
        
        return templates.TemplateResponse("backtesting/results.html", {
            "request": request,
            "user": user,
            "backtests": backtests,
            "strategies": user_strategies,
            "unique_symbols": unique_symbols,
            "current_strategy": strategy_id,
            "current_symbol": symbol,
            "page_title": "Backtest Results"
        })
        
    except Exception as e:
        logger.error(f"Backtest results error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load backtest results")

@router.get("/result/{backtest_id}")
async def backtest_detail(
    request: Request,
    backtest_id: str,
    user: User = Depends(require_auth)
):
    """Detailed backtest result page"""
    try:
        # Get backtest
        backtest = await backtest_repo.get_by_id(backtest_id)
        if not backtest or str(backtest.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        # Get strategy
        strategy = await strategy_repo.get_by_id(backtest.strategy_id)
        
        # Prepare chart data for visualization
        chart_data = prepare_backtest_chart_data(backtest)
        
        return templates.TemplateResponse("backtesting/detail.html", {
            "request": request,
            "user": user,
            "backtest": backtest,
            "strategy": strategy,
            "chart_data": chart_data,
            "page_title": f"Backtest Results - {strategy.name if strategy else 'Unknown'}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest detail error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load backtest details")

@router.get("/compare")
async def compare_backtests_page(
    request: Request,
    user: User = Depends(require_auth),
    backtest_ids: Optional[str] = Query(None)
):
    """Compare multiple backtests"""
    try:
        compared_backtests = []
        
        if backtest_ids:
            # Parse backtest IDs
            ids = backtest_ids.split(',')
            
            for backtest_id in ids:
                backtest = await backtest_repo.get_by_id(backtest_id.strip())
                if backtest and str(backtest.user_id) == str(user.id):
                    strategy = await strategy_repo.get_by_id(backtest.strategy_id)
                    compared_backtests.append({
                        "backtest": backtest,
                        "strategy": strategy
                    })
        
        # Get all user backtests for selection
        all_backtests = await backtest_repo.get_user_backtests(user.id)
        
        # Prepare comparison data
        comparison_data = prepare_comparison_data(compared_backtests)
        
        return templates.TemplateResponse("backtesting/compare.html", {
            "request": request,
            "user": user,
            "compared_backtests": compared_backtests,
            "all_backtests": all_backtests,
            "comparison_data": comparison_data,
            "page_title": "Compare Backtests"
        })
        
    except Exception as e:
        logger.error(f"Compare backtests error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load comparison page")

@router.post("/run")
async def run_backtest(
    background_tasks: BackgroundTasks,
    request: Request,
    strategy_id: str = Form(...),
    symbol: str = Form(...),
    timeframe: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    initial_balance: float = Form(10000.0),
    csrf_token: str = Form(...),
    user: User = Depends(require_auth)
):
    """Start a new backtest"""
    
    # Verify CSRF token
    session_token = request.session.get("csrf_token")
    if not session_token or csrf_token != session_token:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")
    
    try:
        # Validate backtest request
        backtest_request = BacktestRequest(
            strategy_id=strategy_id,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance
        )
        
        # Verify strategy belongs to user
        strategy = await strategy_repo.get_by_id(strategy_id)
        if not strategy or str(strategy.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Parse dates
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
        
        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        # Create backtest record
        backtest = await backtest_repo.create({
            "user_id": user.id,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_dt,
            "end_date": end_dt,
            "initial_balance": initial_balance,
            "status": "running"
        })
        
        # Start backtest in background
        background_tasks.add_task(
            execute_backtest,
            str(backtest.id),
            backtest_request,
            strategy
        )
        
        # Store running backtest info
        running_backtests[str(backtest.id)] = {
            "status": "running",
            "progress": 0,
            "started_at": datetime.utcnow()
        }
        
        return RedirectResponse(
            url=f"/backtesting/status/{backtest.id}",
            status_code=302
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Run backtest error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start backtest")

@router.get("/status/{backtest_id}")
async def backtest_status(
    request: Request,
    backtest_id: str,
    user: User = Depends(require_auth)
):
    """Backtest status page"""
    try:
        # Get backtest
        backtest = await backtest_repo.get_by_id(backtest_id)
        if not backtest or str(backtest.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        # Get running status
        running_status = running_backtests.get(backtest_id, {})
        
        return templates.TemplateResponse("backtesting/status.html", {
            "request": request,
            "user": user,
            "backtest": backtest,
            "running_status": running_status,
            "page_title": "Backtest Status"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get backtest status")

@router.delete("/delete/{backtest_id}")
async def delete_backtest(
    backtest_id: str,
    user: User = Depends(require_auth)
):
    """Delete backtest result"""
    try:
        # Get backtest
        backtest = await backtest_repo.get_by_id(backtest_id)
        if not backtest or str(backtest.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        # Delete backtest
        await backtest_repo.delete(backtest_id)
        
        return JSONResponse(content={
            "success": True,
            "message": "Backtest deleted successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete backtest error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete backtest")

@router.get("/export/{backtest_id}")
async def export_backtest(
    backtest_id: str,
    format: str = Query("json"),
    user: User = Depends(require_auth)
):
    """Export backtest results"""
    try:
        # Get backtest
        backtest = await backtest_repo.get_by_id(backtest_id)
        if not backtest or str(backtest.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        # Get strategy
        strategy = await strategy_repo.get_by_id(backtest.strategy_id)
        
        if format.lower() == "csv":
            # Export as CSV
            content = export_backtest_csv(backtest, strategy)
            media_type = "text/csv"
            extension = "csv"
        else:
            # Export as JSON
            content = export_backtest_json(backtest, strategy)
            media_type = "application/json"
            extension = "json"
        
        filename = f"backtest_{backtest.symbol}_{backtest.timeframe}_{backtest_id[:8]}.{extension}"
        
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export backtest error: {e}")
        raise HTTPException(status_code=500, detail="Failed to export backtest")

# API endpoints
@router.get("/api/status/{backtest_id}")
async def api_backtest_status(
    backtest_id: str,
    user: User = Depends(require_auth)
):
    """Get backtest status via API"""
    try:
        # Get backtest
        backtest = await backtest_repo.get_by_id(backtest_id)
        if not backtest or str(backtest.user_id) != str(user.id):
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        # Get running status
        running_status = running_backtests.get(backtest_id, {})
        
        return JSONResponse(content={
            "backtest_id": backtest_id,
            "status": backtest.status if hasattr(backtest, 'status') else running_status.get("status", "unknown"),
            "progress": running_status.get("progress", 0),
            "started_at": running_status.get("started_at").isoformat() if running_status.get("started_at") else None,
            "completed": backtest.status == "completed" if hasattr(backtest, 'status') else False
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API backtest status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")

async def execute_backtest(backtest_id: str, request: BacktestRequest, strategy):
    """Execute backtest in background"""
    try:
        # Update status
        running_backtests[backtest_id]["status"] = "loading_data"
        running_backtests[backtest_id]["progress"] = 10
        
        # Get historical data
        start_dt = datetime.fromisoformat(request.start_date)
        end_dt = datetime.fromisoformat(request.end_date)
        
        # Calculate required data points
        timeframe_map = {
            "1m": 1, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "4h": 240, "8h": 480, "1d": 1440, "1w": 10080
        }
        
        minutes = timeframe_map.get(request.timeframe, 60)
        total_minutes = int((end_dt - start_dt).total_seconds() / 60)
        limit = min(total_minutes // minutes, 1000)  # Max 1000 candles
        
        market_data = await api_manager.ccxt_client.get_market_data(
            symbol=request.symbol,
            timeframe=request.timeframe,
            limit=limit
        )
        
        # Update status
        running_backtests[backtest_id]["status"] = "running_simulation"
        running_backtests[backtest_id]["progress"] = 30
        
        # Initialize backtesting engine
        engine = BacktestingEngine()
        
        # Run backtest
        results = await engine.run_backtest(
            strategy_config=strategy.config,
            strategy_type=strategy.strategy_type,
            market_data=market_data,
            initial_balance=request.initial_balance,
            start_date=start_dt,
            end_date=end_dt,
            symbol=request.symbol,
            timeframe=request.timeframe
        )
        
        # Update status
        running_backtests[backtest_id]["status"] = "calculating_metrics"
        running_backtests[backtest_id]["progress"] = 80
        
        # Calculate performance metrics
        performance_metrics = calculate_performance_metrics(results, request.initial_balance)
        
        # Update status
        running_backtests[backtest_id]["progress"] = 100
        
        # Save results to database
        await backtest_repo.update(backtest_id, {
            "status": "completed",
            "final_balance": results.get("final_balance", request.initial_balance),
            "total_trades": results.get("total_trades", 0),
            "winning_trades": results.get("winning_trades", 0),
            "losing_trades": results.get("losing_trades", 0),
            "results": performance_metrics,
            "trades_log": results.get("trades", []),
            "completed_at": datetime.utcnow()
        })
        
        # Remove from running backtests
        if backtest_id in running_backtests:
            del running_backtests[backtest_id]
        
    except Exception as e:
        logger.error(f"Backtest execution error: {e}")
        
        # Update with error status
        running_backtests[backtest_id]["status"] = "error"
        running_backtests[backtest_id]["error"] = str(e)
        
        await backtest_repo.update(backtest_id, {
            "status": "error",
            "error": str(e),
            "completed_at": datetime.utcnow()
        })

def calculate_performance_metrics(results: Dict[str, Any], initial_balance: float) -> Dict[str, Any]:
    """Calculate comprehensive performance metrics"""
    
    final_balance = results.get("final_balance", initial_balance)
    trades = results.get("trades", [])
    
    # Basic metrics
    total_return = final_balance - initial_balance
    total_return_pct = (total_return / initial_balance) * 100
    
    total_trades = len(trades)
    winning_trades = sum(1 for trade in trades if trade.get("pnl", 0) > 0)
    losing_trades = total_trades - winning_trades
    win_rate = (winning_trades / max(total_trades, 1)) * 100
    
    # PnL calculations
    profits = [trade.get("pnl", 0) for trade in trades if trade.get("pnl", 0) > 0]
    losses = [abs(trade.get("pnl", 0)) for trade in trades if trade.get("pnl", 0) < 0]
    
    avg_profit = sum(profits) / max(len(profits), 1)
    avg_loss = sum(losses) / max(len(losses), 1)
    profit_factor = sum(profits) / max(sum(losses), 1) if losses else float('inf')
    
    # Drawdown calculation (simplified)
    equity_curve = []
    running_balance = initial_balance
    
    for trade in trades:
        running_balance += trade.get("pnl", 0)
        equity_curve.append(running_balance)
    
    if equity_curve:
        peak = initial_balance
        max_drawdown = 0
        
        for balance in equity_curve:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
    else:
        max_drawdown = 0
    
    # Risk metrics (simplified)
    if len(equity_curve) > 1:
        returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] 
                  for i in range(1, len(equity_curve))]
        volatility = (sum([(r - sum(returns)/len(returns))**2 for r in returns]) / len(returns))**0.5 * 100
        sharpe_ratio = (total_return_pct / max(volatility, 1)) if volatility > 0 else 0
    else:
        volatility = 0
        sharpe_ratio = 0
    
    return {
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 2),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞",
        "max_drawdown": round(max_drawdown, 2),
        "volatility": round(volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 2)
    }

def prepare_backtest_chart_data(backtest) -> Dict[str, Any]:
    """Prepare chart data for backtest visualization"""
    
    trades_log = backtest.trades_log or []
    
    # Prepare equity curve
    equity_points = []
    running_balance = backtest.initial_balance
    
    equity_points.append({
        "time": backtest.start_date.isoformat(),
        "balance": running_balance
    })
    
    for trade in trades_log:
        running_balance += trade.get("pnl", 0)
        equity_points.append({
            "time": trade.get("timestamp", backtest.start_date.isoformat()),
            "balance": running_balance
        })
    
    # Prepare trade markers
    buy_signals = []
    sell_signals = []
    
    for trade in trades_log:
        point = {
            "time": trade.get("timestamp", backtest.start_date.isoformat()),
            "price": trade.get("price", 0),
            "amount": trade.get("amount", 0),
            "pnl": trade.get("pnl", 0)
        }
        
        if trade.get("side") == "buy":
            buy_signals.append(point)
        else:
            sell_signals.append(point)
    
    return {
        "equity_curve": equity_points,
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "symbol": backtest.symbol,
        "timeframe": backtest.timeframe
    }

def prepare_comparison_data(compared_backtests: List) -> Dict[str, Any]:
    """Prepare data for backtest comparison"""
    
    if not compared_backtests:
        return {}
    
    comparison = {
        "metrics": [],
        "equity_curves": [],
        "summary": {}
    }
    
    # Collect metrics for comparison
    metrics_keys = [
        "total_return_pct", "win_rate", "max_drawdown", 
        "total_trades", "profit_factor", "sharpe_ratio"
    ]
    
    for item in compared_backtests:
        backtest = item["backtest"]
        strategy = item["strategy"]
        
        metrics = backtest.results or {}
        
        comparison["metrics"].append({
            "name": strategy.name if strategy else "Unknown",
            "metrics": {key: metrics.get(key, 0) for key in metrics_keys}
        })
        
        # Add equity curve
        chart_data = prepare_backtest_chart_data(backtest)
        comparison["equity_curves"].append({
            "name": strategy.name if strategy else "Unknown",
            "data": chart_data["equity_curve"]
        })
    
    # Calculate summary statistics
    if compared_backtests:
        returns = [b["backtest"].results.get("total_return_pct", 0) for b in compared_backtests]
        win_rates = [b["backtest"].results.get("win_rate", 0) for b in compared_backtests]
        
        comparison["summary"] = {
            "best_return": max(returns) if returns else 0,
            "worst_return": min(returns) if returns else 0,
            "avg_return": sum(returns) / len(returns) if returns else 0,
            "best_win_rate": max(win_rates) if win_rates else 0,
            "avg_win_rate": sum(win_rates) / len(win_rates) if win_rates else 0
        }
    
    return comparison

def export_backtest_json(backtest, strategy) -> str:
    """Export backtest as JSON"""
    
    export_data = {
        "backtest_id": str(backtest.id),
        "strategy": {
            "name": strategy.name if strategy else "Unknown",
            "type": strategy.strategy_type if strategy else "unknown",
            "config": strategy.config if strategy else {}
        },
        "parameters": {
            "symbol": backtest.symbol,
            "timeframe": backtest.timeframe,
            "start_date": backtest.start_date.isoformat(),
            "end_date": backtest.end_date.isoformat(),
            "initial_balance": backtest.initial_balance
        },
        "results": backtest.results or {},
        "trades": backtest.trades_log or [],
        "exported_at": datetime.utcnow().isoformat()
    }
    
    return json.dumps(export_data, indent=2)

def export_backtest_csv(backtest, strategy) -> str:
    """Export backtest as CSV"""
    
    trades_log = backtest.trades_log or []
    
    # CSV header
    csv_lines = [
        "Timestamp,Side,Symbol,Amount,Price,PnL,Balance"
    ]
    
    running_balance = backtest.initial_balance
    
    for trade in trades_log:
        running_balance += trade.get("pnl", 0)
        
        csv_lines.append(
            f"{trade.get('timestamp', '')},{trade.get('side', '')},"
            f"{backtest.symbol},{trade.get('amount', 0)},{trade.get('price', 0)},"
            f"{trade.get('pnl', 0)},{running_balance}"
        )
    
    return "\n".join(csv_lines)
