# src/database/models/backtest.py

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pydantic import Field, validator
from enum import Enum
import statistics
from src.database.models.base import (
    BaseDBModel, BaseRepository, TimestampMixin, 
    UserOwnershipMixin, PyObjectId
)

class BacktestStatus(str, Enum):
    """Backtest execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BacktestTradeLog(BaseDBModel):
    """Individual trade log entry for backtesting"""
    
    timestamp: datetime = Field(..., description="Trade timestamp")
    symbol: str = Field(..., description="Trading pair")
    side: str = Field(..., description="buy or sell")
    amount: float = Field(..., description="Trade amount")
    price: float = Field(..., description="Execution price")
    fee: float = Field(default=0.0, description="Trading fee")
    signal_type: str = Field(..., description="Signal that triggered trade")
    balance_before: float = Field(..., description="Balance before trade")
    balance_after: float = Field(..., description="Balance after trade")
    pnl: float = Field(default=0.0, description="Trade PnL")
    
    # Additional metadata
    indicators: Dict[str, float] = Field(default={}, description="Indicator values at trade time")
    notes: Optional[str] = Field(None, description="Trade notes")
    
    @property
    def collection_name(self) -> str:
        return "backtest_trade_logs"

class BacktestPerformanceMetrics(BaseDBModel):
    """Backtest performance metrics"""
    
    # Basic metrics
    total_return: float = Field(default=0.0, description="Total return amount")
    total_return_pct: float = Field(default=0.0, description="Total return percentage")
    total_trades: int = Field(default=0, description="Total number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")
    
    # Performance ratios
    win_rate: float = Field(default=0.0, description="Win rate percentage")
    profit_factor: float = Field(default=0.0, description="Profit factor")
    sharpe_ratio: float = Field(default=0.0, description="Sharpe ratio")
    sortino_ratio: float = Field(default=0.0, description="Sortino ratio")
    calmar_ratio: float = Field(default=0.0, description="Calmar ratio")
    
    # Risk metrics
    max_drawdown: float = Field(default=0.0, description="Maximum drawdown")
    max_drawdown_pct: float = Field(default=0.0, description="Maximum drawdown percentage")
    max_drawdown_duration: int = Field(default=0, description="Max drawdown duration in days")
    volatility: float = Field(default=0.0, description="Return volatility")
    var_95: float = Field(default=0.0, description="Value at Risk (95%)")
    
    # Trade statistics
    avg_trade_return: float = Field(default=0.0, description="Average trade return")
    avg_winning_trade: float = Field(default=0.0, description="Average winning trade")
    avg_losing_trade: float = Field(default=0.0, description="Average losing trade")
    largest_winning_trade: float = Field(default=0.0, description="Largest winning trade")
    largest_losing_trade: float = Field(default=0.0, description="Largest losing trade")
    
    # Time-based metrics
    avg_trade_duration: float = Field(default=0.0, description="Average trade duration in hours")
    avg_time_between_trades: float = Field(default=0.0, description="Average time between trades in hours")
    
    # Additional metrics
    beta: float = Field(default=0.0, description="Beta relative to benchmark")
    alpha: float = Field(default=0.0, description="Alpha")
    correlation: float = Field(default=0.0, description="Correlation with benchmark")
    
    @property
    def collection_name(self) -> str:
        return "backtest_performance_metrics"
    
    def calculate_basic_metrics(self, trades: List[BacktestTradeLog], 
                               initial_balance: float, final_balance: float):
        """Calculate basic performance metrics from trades"""
        if not trades:
            return
        
        self.total_trades = len(trades)
        self.total_return = final_balance - initial_balance
        self.total_return_pct = (self.total_return / initial_balance) * 100 if initial_balance > 0 else 0
        
        # Categorize trades
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        self.winning_trades = len(winning_trades)
        self.losing_trades = len(losing_trades)
        self.win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
        
        # Trade statistics
        if trades:
            self.avg_trade_return = sum(t.pnl for t in trades) / len(trades)
        
        if winning_trades:
            self.avg_winning_trade = sum(t.pnl for t in winning_trades) / len(winning_trades)
            self.largest_winning_trade = max(t.pnl for t in winning_trades)
        
        if losing_trades:
            self.avg_losing_trade = sum(t.pnl for t in losing_trades) / len(losing_trades)
            self.largest_losing_trade = min(t.pnl for t in losing_trades)
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        self.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    def calculate_advanced_metrics(self, daily_returns: List[float], 
                                 benchmark_returns: List[float] = None):
        """Calculate advanced performance metrics"""
        if not daily_returns:
            return
        
        # Volatility (annualized)
        if len(daily_returns) > 1:
            self.volatility = statistics.stdev(daily_returns) * (252 ** 0.5)  # Annualized
        
        # Sharpe ratio (assuming risk-free rate of 2%)
        risk_free_rate = 0.02
        avg_return = statistics.mean(daily_returns) * 252  # Annualized
        if self.volatility > 0:
            self.sharpe_ratio = (avg_return - risk_free_rate) / self.volatility
        
        # Sortino ratio (downside deviation)
        downside_returns = [r for r in daily_returns if r < 0]
        if downside_returns:
            downside_deviation = statistics.stdev(downside_returns) * (252 ** 0.5)
            if downside_deviation > 0:
                self.sortino_ratio = (avg_return - risk_free_rate) / downside_deviation
        
        # Value at Risk (95%)
        if len(daily_returns) >= 20:
            sorted_returns = sorted(daily_returns)
            var_index = int(len(sorted_returns) * 0.05)
            self.var_95 = sorted_returns[var_index]
        
        # Beta and correlation with benchmark
        if benchmark_returns and len(benchmark_returns) == len(daily_returns):
            try:
                # Calculate correlation
                n = len(daily_returns)
                if n > 1:
                    mean_strategy = statistics.mean(daily_returns)
                    mean_benchmark = statistics.mean(benchmark_returns)
                    
                    numerator = sum((daily_returns[i] - mean_strategy) * 
                                  (benchmark_returns[i] - mean_benchmark) for i in range(n))
                    denominator = (sum((daily_returns[i] - mean_strategy) ** 2 for i in range(n)) *
                                 sum((benchmark_returns[i] - mean_benchmark) ** 2 for i in range(n))) ** 0.5
                    
                    if denominator > 0:
                        self.correlation = numerator / denominator
                        
                        # Beta calculation
                        benchmark_variance = statistics.variance(benchmark_returns)
                        if benchmark_variance > 0:
                            covariance = numerator / (n - 1)
                            self.beta = covariance / benchmark_variance
                            
                            # Alpha calculation
                            benchmark_return = statistics.mean(benchmark_returns) * 252
                            self.alpha = avg_return - (risk_free_rate + self.beta * (benchmark_return - risk_free_rate))
            except:
                pass  # Skip if calculation fails

class Backtest(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """Backtest execution and results"""
    
    # Strategy reference
    strategy_id: PyObjectId = Field(..., description="Strategy ID")
    strategy_name: str = Field(..., description="Strategy name")
    strategy_config: Dict[str, Any] = Field(..., description="Strategy configuration snapshot")
    
    # Backtest parameters
    symbol: str = Field(..., description="Trading pair")
    timeframe: str = Field(..., description="Timeframe used")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    
    # Initial conditions
    initial_balance: float = Field(..., description="Starting balance")
    commission: float = Field(default=0.001, description="Commission rate")
    slippage: float = Field(default=0.0001, description="Slippage rate")
    
    # Execution tracking
    status: BacktestStatus = Field(default=BacktestStatus.PENDING, description="Execution status")
    progress: float = Field(default=0.0, ge=0, le=100, description="Execution progress %")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None  # seconds
    
    # Results
    final_balance: float = Field(default=0.0, description="Final balance")
    performance_metrics: Optional[BacktestPerformanceMetrics] = None
    
    # Trade logs
    trades_log: List[BacktestTradeLog] = Field(default=[], description="Detailed trade history")
    
    # Error handling
    error_message: Optional[str] = None
    warnings: List[str] = Field(default=[], description="Warnings during execution")
    
    # Metadata
    data_points_processed: int = Field(default=0, description="Number of data points processed")
    notes: Optional[str] = Field(None, max_length=2000, description="Backtest notes")
    tags: List[str] = Field(default=[], description="Backtest tags")
    
    @property
    def collection_name(self) -> str:
        return "backtests"
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()
    
    def start_execution(self):
        """Mark backtest as started"""
        self.status = BacktestStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self.progress = 0.0
    
    def update_progress(self, progress: float):
        """Update execution progress"""
        self.progress = max(0.0, min(100.0, progress))
    
    def complete_execution(self, final_balance: float, trades: List[BacktestTradeLog]):
        """Mark backtest as completed and calculate results"""
        self.status = BacktestStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.progress = 100.0
        self.final_balance = final_balance
        self.trades_log = trades
        
        if self.started_at:
            execution_time = (self.completed_at - self.started_at).total_seconds()
            self.execution_time = execution_time
        
        # Calculate performance metrics
        self.performance_metrics = BacktestPerformanceMetrics()
        self.performance_metrics.calculate_basic_metrics(
            trades, self.initial_balance, final_balance
        )
    
    def fail_execution(self, error_message: str):
        """Mark backtest as failed"""
        self.status = BacktestStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message
    
    def get_duration_days(self) -> int:
        """Get backtest duration in days"""
        return (self.end_date - self.start_date).days
    
    def get_execution_time_formatted(self) -> str:
        """Get formatted execution time"""
        if not self.execution_time:
            return "N/A"
        
        if self.execution_time < 60:
            return f"{self.execution_time:.1f}s"
        elif self.execution_time < 3600:
            return f"{self.execution_time/60:.1f}m"
        else:
            return f"{self.execution_time/3600:.1f}h"
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Return backtest summary"""
        summary = {
            "id": str(self.id),
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "duration_days": self.get_duration_days(),
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "status": self.status,
            "progress": self.progress,
            "execution_time": self.get_execution_time_formatted(),
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }
        
        if self.performance_metrics:
            summary.update({
                "total_return": self.performance_metrics.total_return,
                "total_return_pct": self.performance_metrics.total_return_pct,
                "total_trades": self.performance_metrics.total_trades,
                "win_rate": self.performance_metrics.win_rate,
                "sharpe_ratio": self.performance_metrics.sharpe_ratio,
                "max_drawdown_pct": self.performance_metrics.max_drawdown_pct
            })
        
        return summary

class BacktestRepository(BaseRepository[Backtest]):
    """Repository for Backtest operations"""
    
    def __init__(self):
        super().__init__(Backtest)
    
    async def get_user_backtests(self, user_id: str, skip: int = 0, 
                               limit: int = 50) -> List[Backtest]:
        """Get user backtests"""
        return await self.get_many(
            filter_dict={"user_id": PyObjectId(user_id)},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
    
    async def get_strategy_backtests(self, strategy_id: str, 
                                   skip: int = 0, limit: int = 20) -> List[Backtest]:
        """Get backtests for specific strategy"""
        return await self.get_many(
            filter_dict={"strategy_id": PyObjectId(strategy_id)},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
    
    async def get_running_backtests(self, user_id: str = None) -> List[Backtest]:
        """Get currently running backtests"""
        filter_dict = {"status": BacktestStatus.RUNNING}
        if user_id:
            filter_dict["user_id"] = PyObjectId(user_id)
        
        return await self.get_many(filter_dict, sort=[("started_at", 1)])
    
    async def create_backtest(self, user_id: str, strategy_id: str, strategy_name: str,
                            strategy_config: Dict[str, Any], symbol: str, timeframe: str,
                            start_date: datetime, end_date: datetime, 
                            initial_balance: float, **kwargs) -> Backtest:
        """Create new backtest"""
        backtest_data = {
            "user_id": PyObjectId(user_id),
            "strategy_id": PyObjectId(strategy_id),
            "strategy_name": strategy_name,
            "strategy_config": strategy_config,
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "initial_balance": initial_balance,
            **kwargs
        }
        
        return await self.create(backtest_data)
    
    async def update_progress(self, backtest_id: str, progress: float) -> bool:
        """Update backtest progress"""
        result = await self.update(backtest_id, {"progress": progress})
        return result is not None
    
    async def complete_backtest(self, backtest_id: str, final_balance: float,
                              trades: List[Dict[str, Any]], 
                              performance_metrics: Dict[str, Any] = None) -> Optional[Backtest]:
        """Complete backtest execution"""
        backtest = await self.get_by_id(backtest_id)
        if not backtest:
            return None
        
        # Convert trade dicts to BacktestTradeLog objects
        trade_logs = [BacktestTradeLog(**trade) for trade in trades]
        
        update_data = {
            "status": BacktestStatus.COMPLETED,
            "completed_at": datetime.now(timezone.utc),
            "progress": 100.0,
            "final_balance": final_balance,
            "trades_log": [trade.dict() for trade in trade_logs]
        }
        
        # Calculate execution time
        if backtest.started_at:
            execution_time = (update_data["completed_at"] - backtest.started_at).total_seconds()
            update_data["execution_time"] = execution_time
        
        # Add performance metrics
        if performance_metrics:
            update_data["performance_metrics"] = performance_metrics
        else:
            # Calculate basic metrics
            metrics = BacktestPerformanceMetrics()
            metrics.calculate_basic_metrics(trade_logs, backtest.initial_balance, final_balance)
            update_data["performance_metrics"] = metrics.dict()
        
        return await self.update(backtest_id, update_data)
    
    async def fail_backtest(self, backtest_id: str, error_message: str) -> bool:
        """Fail backtest execution"""
        update_data = {
            "status": BacktestStatus.FAILED,
            "completed_at": datetime.now(timezone.utc),
            "error_message": error_message
        }
        
        result = await self.update(backtest_id, update_data)
        return result is not None
    
    async def get_backtest_statistics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get backtest statistics for user"""
        from_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        backtests = await self.get_many({
            "user_id": PyObjectId(user_id),
            "created_at": {"$gte": from_date}
        })
        
        completed_backtests = [bt for bt in backtests if bt.status == BacktestStatus.COMPLETED]
        
        if not completed_backtests:
            return {
                "total_backtests": len(backtests),
                "completed_backtests": 0,
                "avg_return": 0.0,
                "best_strategy": None,
                "most_tested_symbol": None
            }
        
        # Calculate statistics
        avg_return = statistics.mean([bt.performance_metrics.total_return_pct 
                                    for bt in completed_backtests 
                                    if bt.performance_metrics])
        
        # Find best performing strategy
        best_backtest = max(completed_backtests, 
                          key=lambda bt: bt.performance_metrics.total_return_pct 
                          if bt.performance_metrics else 0)
        
        # Most tested symbol
        symbols = [bt.symbol for bt in backtests]
        most_tested_symbol = max(set(symbols), key=symbols.count) if symbols else None
        
        return {
            "total_backtests": len(backtests),
            "completed_backtests": len(completed_backtests),
            "success_rate": (len(completed_backtests) / len(backtests)) * 100 if backtests else 0,
            "avg_return": avg_return,
            "best_strategy": best_backtest.strategy_name if best_backtest else None,
            "best_return": best_backtest.performance_metrics.total_return_pct if best_backtest and best_backtest.performance_metrics else 0,
            "most_tested_symbol": most_tested_symbol,
            "symbols_tested": len(set(symbols))
        }

# Repository instance
backtest_repository = BacktestRepository()