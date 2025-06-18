# src/strategies/analytics.py

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import statistics
import math
import logging

from .base import BaseStrategy, Signal, SignalAction

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_return_pct: float = 0.0
    
    # Risk metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    
    # Trade analysis
    avg_win: float = 0.0
    avg_loss: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_trade_duration: float = 0.0  # in hours
    
    # Advanced metrics
    calmar_ratio: float = 0.0
    recovery_factor: float = 0.0
    volatility: float = 0.0
    downside_deviation: float = 0.0
    
    # Time-based analysis
    daily_returns: List[float] = field(default_factory=list)
    monthly_returns: List[float] = field(default_factory=list)
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

@dataclass
class TradeAnalysis:
    """Individual trade analysis"""
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    pnl_pct: Optional[float]
    duration_hours: Optional[float]
    fees: float = 0.0
    signal_reason: str = ""

class PerformanceAnalyzer:
    """
    Analyzes strategy performance and provides detailed metrics
    """
    
    def __init__(self):
        self.trade_history: Dict[str, List[TradeAnalysis]] = {}
        self.portfolio_history: List[Dict[str, Any]] = []
        self.benchmark_data: List[float] = []
        
        logger.info("Performance analyzer initialized")
    
    def add_trade(self, strategy_id: str, trade: TradeAnalysis):
        """
        Add trade to analysis
        
        Args:
            strategy_id: Strategy identifier
            trade: Trade analysis data
        """
        if strategy_id not in self.trade_history:
            self.trade_history[strategy_id] = []
        
        self.trade_history[strategy_id].append(trade)
    
    def calculate_metrics(self, strategy_id: str, initial_balance: float = 10000.0) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics for a strategy
        
        Args:
            strategy_id: Strategy identifier
            initial_balance: Initial portfolio balance
            
        Returns:
            Performance metrics
        """
        trades = self.trade_history.get(strategy_id, [])
        if not trades:
            return PerformanceMetrics()
        
        # Filter completed trades
        completed_trades = [t for t in trades if t.exit_time and t.pnl is not None]
        
        if not completed_trades:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        
        # Basic metrics
        metrics.total_trades = len(completed_trades)
        metrics.winning_trades = len([t for t in completed_trades if t.pnl > 0])
        metrics.losing_trades = len([t for t in completed_trades if t.pnl < 0])
        metrics.total_pnl = sum(t.pnl for t in completed_trades)
        metrics.total_return_pct = (metrics.total_pnl / initial_balance) * 100
        
        # Win rate
        metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100 if metrics.total_trades > 0 else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in completed_trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in completed_trades if t.pnl < 0))
        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        # Trade analysis
        winning_trades = [t for t in completed_trades if t.pnl > 0]
        losing_trades = [t for t in completed_trades if t.pnl < 0]
        
        metrics.avg_win = statistics.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        metrics.avg_loss = statistics.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        metrics.best_trade = max([t.pnl for t in completed_trades]) if completed_trades else 0
        metrics.worst_trade = min([t.pnl for t in completed_trades]) if completed_trades else 0
        
        # Average trade duration
        durations = [t.duration_hours for t in completed_trades if t.duration_hours]
        metrics.avg_trade_duration = statistics.mean(durations) if durations else 0
        
        # Calculate advanced metrics
        metrics = self._calculate_risk_metrics(metrics, completed_trades, initial_balance)
        metrics = self._calculate_drawdown(metrics, completed_trades, initial_balance)
        metrics = self._calculate_consecutive_stats(metrics, completed_trades)
        
        return metrics
    
    def _calculate_risk_metrics(self, metrics: PerformanceMetrics, trades: List[TradeAnalysis], 
                               initial_balance: float) -> PerformanceMetrics:
        """Calculate risk-related metrics"""
        if not trades:
            return metrics
        
        # Get daily returns
        returns = self._calculate_daily_returns(trades, initial_balance)
        metrics.daily_returns = returns
        
        if len(returns) < 2:
            return metrics
        
        # Volatility (standard deviation of returns)
        metrics.volatility = statistics.stdev(returns) * math.sqrt(252)  # Annualized
        
        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        avg_return = statistics.mean(returns)
        if metrics.volatility > 0:
            metrics.sharpe_ratio = (avg_return * 252 - risk_free_rate) / metrics.volatility
        
        # Sortino ratio (downside deviation)
        negative_returns = [r for r in returns if r < 0]
        if negative_returns:
            metrics.downside_deviation = statistics.stdev(negative_returns) * math.sqrt(252)
            if metrics.downside_deviation > 0:
                metrics.sortino_ratio = (avg_return * 252 - risk_free_rate) / metrics.downside_deviation
        
        # Calmar ratio
        if metrics.max_drawdown_pct > 0:
            metrics.calmar_ratio = metrics.total_return_pct / metrics.max_drawdown_pct
        
        return metrics
    
    def _calculate_drawdown(self, metrics: PerformanceMetrics, trades: List[TradeAnalysis], 
                           initial_balance: float) -> PerformanceMetrics:
        """Calculate maximum drawdown"""
        balance = initial_balance
        peak_balance = initial_balance
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        
        for trade in sorted(trades, key=lambda t: t.exit_time):
            balance += trade.pnl
            
            if balance > peak_balance:
                peak_balance = balance
            
            drawdown = peak_balance - balance
            drawdown_pct = (drawdown / peak_balance) * 100 if peak_balance > 0 else 0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        metrics.max_drawdown = max_drawdown
        metrics.max_drawdown_pct = max_drawdown_pct
        
        # Recovery factor
        if max_drawdown > 0:
            metrics.recovery_factor = metrics.total_pnl / max_drawdown
        
        return metrics
    
    def _calculate_consecutive_stats(self, metrics: PerformanceMetrics, 
                                    trades: List[TradeAnalysis]) -> PerformanceMetrics:
        """Calculate consecutive wins/losses statistics"""
        if not trades:
            return metrics
        
        sorted_trades = sorted(trades, key=lambda t: t.exit_time)
        
        current_wins = 0
        current_losses = 0
        max_wins = 0
        max_losses = 0
        
        for trade in sorted_trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif trade.pnl < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        metrics.consecutive_wins = current_wins
        metrics.consecutive_losses = current_losses
        metrics.max_consecutive_wins = max_wins
        metrics.max_consecutive_losses = max_losses
        
        return metrics
    
    def _calculate_daily_returns(self, trades: List[TradeAnalysis], initial_balance: float) -> List[float]:
        """Calculate daily returns from trades"""
        if not trades:
            return []
        
        # Group trades by day
        daily_pnl = {}
        for trade in trades:
            if trade.exit_time:
                date = trade.exit_time.date()
                if date not in daily_pnl:
                    daily_pnl[date] = 0
                daily_pnl[date] += trade.pnl
        
        # Calculate daily returns as percentage
        balance = initial_balance
        returns = []
        
        for date in sorted(daily_pnl.keys()):
            daily_return = (daily_pnl[date] / balance) * 100
            returns.append(daily_return)
            balance += daily_pnl[date]
        
        return returns
    
    def compare_strategies(self, strategy_ids: List[str], 
                          initial_balance: float = 10000.0) -> Dict[str, Any]:
        """
        Compare performance of multiple strategies
        
        Args:
            strategy_ids: List of strategy identifiers
            initial_balance: Initial balance for comparison
            
        Returns:
            Comparison results
        """
        comparison = {
            'strategies': {},
            'ranking': {},
            'summary': {}
        }
        
        # Calculate metrics for each strategy
        all_metrics = {}
        for strategy_id in strategy_ids:
            metrics = self.calculate_metrics(strategy_id, initial_balance)
            all_metrics[strategy_id] = metrics
            
            comparison['strategies'][strategy_id] = {
                'total_return_pct': metrics.total_return_pct,
                'win_rate': metrics.win_rate,
                'sharpe_ratio': metrics.sharpe_ratio,
                'max_drawdown_pct': metrics.max_drawdown_pct,
                'total_trades': metrics.total_trades,
                'profit_factor': metrics.profit_factor
            }
        
        # Rank strategies by different metrics
        ranking_metrics = ['total_return_pct', 'sharpe_ratio', 'win_rate', 'profit_factor']
        
        for metric in ranking_metrics:
            sorted_strategies = sorted(
                strategy_ids,
                key=lambda s: getattr(all_metrics[s], metric, 0),
                reverse=True
            )
            comparison['ranking'][metric] = sorted_strategies
        
        # Overall ranking (weighted score)
        strategy_scores = {}
        for strategy_id in strategy_ids:
            metrics = all_metrics[strategy_id]
            
            # Weighted score calculation
            score = (
                metrics.total_return_pct * 0.3 +
                metrics.sharpe_ratio * 10 * 0.25 +  # Scale Sharpe ratio
                metrics.win_rate * 0.2 +
                (100 - metrics.max_drawdown_pct) * 0.15 +  # Inverse drawdown
                min(metrics.profit_factor, 10) * 10 * 0.1  # Cap and scale profit factor
            )
            strategy_scores[strategy_id] = score
        
        comparison['ranking']['overall'] = sorted(
            strategy_ids,
            key=lambda s: strategy_scores[s],
            reverse=True
        )
        
        # Summary statistics
        if all_metrics:
            comparison['summary'] = {
                'best_return': max(m.total_return_pct for m in all_metrics.values()),
                'worst_return': min(m.total_return_pct for m in all_metrics.values()),
                'avg_return': statistics.mean(m.total_return_pct for m in all_metrics.values()),
                'best_sharpe': max(m.sharpe_ratio for m in all_metrics.values()),
                'avg_win_rate': statistics.mean(m.win_rate for m in all_metrics.values()),
                'total_trades': sum(m.total_trades for m in all_metrics.values())
            }
        
        return comparison
    
    def generate_performance_report(self, strategy_id: str, 
                                   initial_balance: float = 10000.0) -> Dict[str, Any]:
        """
        Generate comprehensive performance report
        
        Args:
            strategy_id: Strategy identifier
            initial_balance: Initial balance
            
        Returns:
            Detailed performance report
        """
        metrics = self.calculate_metrics(strategy_id, initial_balance)
        trades = self.trade_history.get(strategy_id, [])
        completed_trades = [t for t in trades if t.exit_time and t.pnl is not None]
        
        # Monthly performance
        monthly_performance = self._calculate_monthly_performance(completed_trades)
        
        # Symbol performance
        symbol_performance = self._calculate_symbol_performance(completed_trades)
        
        # Trade distribution
        trade_distribution = self._calculate_trade_distribution(completed_trades)
        
        report = {
            'strategy_id': strategy_id,
            'report_date': datetime.now().isoformat(),
            'summary': {
                'total_return': f"{metrics.total_return_pct:.2f}%",
                'total_trades': metrics.total_trades,
                'win_rate': f"{metrics.win_rate:.1f}%",
                'profit_factor': f"{metrics.profit_factor:.2f}",
                'sharpe_ratio': f"{metrics.sharpe_ratio:.2f}",
                'max_drawdown': f"{metrics.max_drawdown_pct:.2f}%"
            },
            'detailed_metrics': metrics,
            'monthly_performance': monthly_performance,
            'symbol_performance': symbol_performance,
            'trade_distribution': trade_distribution,
            'recent_trades': completed_trades[-10:] if completed_trades else []  # Last 10 trades
        }
        
        return report
    
    def _calculate_monthly_performance(self, trades: List[TradeAnalysis]) -> Dict[str, float]:
        """Calculate monthly performance breakdown"""
        monthly_pnl = {}
        
        for trade in trades:
            if trade.exit_time:
                month_key = trade.exit_time.strftime('%Y-%m')
                if month_key not in monthly_pnl:
                    monthly_pnl[month_key] = 0
                monthly_pnl[month_key] += trade.pnl
        
        return monthly_pnl
    
    def _calculate_symbol_performance(self, trades: List[TradeAnalysis]) -> Dict[str, Dict[str, Any]]:
        """Calculate performance by trading symbol"""
        symbol_stats = {}
        
        for trade in trades:
            symbol = trade.symbol
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    'trades': 0,
                    'total_pnl': 0,
                    'wins': 0,
                    'losses': 0
                }
            
            symbol_stats[symbol]['trades'] += 1
            symbol_stats[symbol]['total_pnl'] += trade.pnl
            
            if trade.pnl > 0:
                symbol_stats[symbol]['wins'] += 1
            else:
                symbol_stats[symbol]['losses'] += 1
        
        # Calculate win rates
        for symbol, stats in symbol_stats.items():
            stats['win_rate'] = (stats['wins'] / stats['trades']) * 100 if stats['trades'] > 0 else 0
        
        return symbol_stats
    
    def _calculate_trade_distribution(self, trades: List[TradeAnalysis]) -> Dict[str, Any]:
        """Calculate trade distribution statistics"""
        if not trades:
            return {}
        
        pnl_values = [t.pnl for t in trades]
        
        return {
            'profit_trades': len([p for p in pnl_values if p > 0]),
            'loss_trades': len([p for p in pnl_values if p < 0]),
            'breakeven_trades': len([p for p in pnl_values if p == 0]),
            'avg_profit': statistics.mean([p for p in pnl_values if p > 0]) if any(p > 0 for p in pnl_values) else 0,
            'avg_loss': statistics.mean([p for p in pnl_values if p < 0]) if any(p < 0 for p in pnl_values) else 0,
            'median_pnl': statistics.median(pnl_values),
            'pnl_std_dev': statistics.stdev(pnl_values) if len(pnl_values) > 1 else 0
        }