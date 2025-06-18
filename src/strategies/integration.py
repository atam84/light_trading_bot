# src/strategies/integration.py

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import asyncio
import logging
from dataclasses import dataclass, field
import json
import yaml
from pathlib import Path

from .base import BaseStrategy, Signal, MarketData, StrategyConfig, StrategyType
from .manager import StrategyManager
from .config import StrategyConfigManager
from .factory import StrategyFactory
from .analytics import PerformanceAnalyzer, TradeAnalysis
from .signals import SignalProcessor, ProcessedSignal

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005   # 0.05%
    symbols: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=lambda: ['1h'])

@dataclass
class BacktestResult:
    """Backtesting result"""
    strategy_id: str
    config: BacktestConfig
    final_balance: float
    total_return_pct: float
    total_trades: int
    win_rate: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trade_history: List[TradeAnalysis]
    performance_chart: Optional[Dict[str, Any]] = None

class StrategyIntegration:
    """
    Main integration class that coordinates all strategy components
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.strategy_factory = StrategyFactory()
        self.strategy_manager = self.strategy_factory.strategy_manager
        self.config_manager = self.strategy_factory.config_manager
        self.signal_processor = SignalProcessor()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Market data cache
        self.market_data_cache: Dict[str, List[MarketData]] = {}
        
        # Real-time processing
        self.real_time_enabled = False
        self.processing_task = None
        
        # Callbacks
        self.trade_callbacks: List[Callable] = []
        
        # Setup signal processing
        self._setup_signal_processing()
        
        logger.info("Strategy integration initialized")
    
    def _setup_signal_processing(self):
        """Setup signal processing callbacks"""
        
        async def on_signal_processed(processed_signal: ProcessedSignal):
            """Handle processed signals"""
            signal = processed_signal.original_signal
            
            if processed_signal.status.value == 'confirmed':
                logger.info(f"Confirmed signal: {signal.symbol} {signal.action.value} "
                           f"at {signal.price} (confidence: {signal.confidence:.2f})")
                
                # Notify trade callbacks
                for callback in self.trade_callbacks:
                    try:
                        await callback(signal) if asyncio.iscoroutinefunction(callback) else callback(signal)
                    except Exception as e:
                        logger.error(f"Trade callback error: {e}")
        
        self.signal_processor.add_callback(on_signal_processed)
    
    def add_trade_callback(self, callback: Callable):
        """Add callback for trade signals"""
        self.trade_callbacks.append(callback)
    
    async def create_and_test_strategy(self, template_name: str, symbol: str, 
                                     timeframe: str = "1h", test_days: int = 30,
                                     custom_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create strategy and run quick backtest
        
        Args:
            template_name: Strategy template name
            symbol: Trading symbol
            timeframe: Trading timeframe
            test_days: Days to backtest
            custom_params: Custom parameters
            
        Returns:
            Strategy creation and test results
        """
        # Create strategy
        strategy_name = f"{template_name}_{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            strategy_id = self.strategy_factory.create_from_template(
                template_name=template_name,
                name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
                overrides=custom_params
            )
            
            # Run quick backtest
            end_date = datetime.now()
            start_date = end_date - timedelta(days=test_days)
            
            backtest_config = BacktestConfig(
                start_date=start_date,
                end_date=end_date,
                symbols=[symbol],
                timeframes=[timeframe]
            )
            
            backtest_result = await self.run_backtest(strategy_id, backtest_config)
            
            return {
                'strategy_id': strategy_id,
                'strategy_name': strategy_name,
                'creation_success': True,
                'backtest_result': backtest_result,
                'recommendations': self._generate_strategy_recommendations(backtest_result)
            }
            
        except Exception as e:
            logger.error(f"Failed to create and test strategy: {e}")
            return {
                'creation_success': False,
                'error': str(e)
            }
    
    async def run_backtest(self, strategy_id: str, config: BacktestConfig) -> BacktestResult:
        """
        Run comprehensive backtest for strategy
        
        Args:
            strategy_id: Strategy to backtest
            config: Backtest configuration
            
        Returns:
            Backtest results
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy '{strategy_id}' not found")
        
        logger.info(f"Running backtest for {strategy_id}: {config.start_date} to {config.end_date}")
        
        # Reset strategy state
        strategy.reset()
        
        # Initialize simulation
        balance = config.initial_balance
        positions = {}
        trade_history = []
        balance_history = []
        
        # Get historical data (simulated for now)
        historical_data = await self._get_historical_data(config)
        
        # Process each data point
        for market_data in historical_data:
            # Generate signal
            signal = await strategy.analyze(market_data)
            
            if signal:
                # Process trade
                trade_result = self._simulate_trade(
                    signal, market_data, balance, positions, config
                )
                
                if trade_result:
                    balance += trade_result['pnl']
                    trade_history.append(trade_result['trade'])
                    
                    # Update strategy position tracking
                    if signal.action.value == 'buy':
                        strategy.update_position(
                            signal.symbol, 'buy', signal.price, trade_result['quantity']
                        )
                    elif signal.action.value == 'sell' and signal.symbol in strategy.positions:
                        strategy.close_position(signal.symbol, signal.price)
            
            # Record balance
            balance_history.append({
                'timestamp': market_data.timestamp,
                'balance': balance
            })
        
        # Calculate final metrics
        final_balance = balance
        total_return_pct = ((final_balance - config.initial_balance) / config.initial_balance) * 100
        
        # Analyze trades
        for trade in trade_history:
            self.performance_analyzer.add_trade(strategy_id, trade)
        
        metrics = self.performance_analyzer.calculate_metrics(strategy_id, config.initial_balance)
        
        result = BacktestResult(
            strategy_id=strategy_id,
            config=config,
            final_balance=final_balance,
            total_return_pct=total_return_pct,
            total_trades=len(trade_history),
            win_rate=metrics.win_rate,
            max_drawdown_pct=metrics.max_drawdown_pct,
            sharpe_ratio=metrics.sharpe_ratio,
            trade_history=trade_history,
            performance_chart=self._generate_performance_chart(balance_history)
        )
        
        logger.info(f"Backtest completed: {total_return_pct:.2f}% return, {len(trade_history)} trades")
        return result
    
    async def start_real_time_processing(self, symbols: List[str], timeframes: List[str]):
        """
        Start real-time strategy processing
        
        Args:
            symbols: Symbols to monitor
            timeframes: Timeframes to process
        """
        if self.real_time_enabled:
            logger.warning("Real-time processing already running")
            return
        
        self.real_time_enabled = True
        
        async def processing_loop():
            while self.real_time_enabled:
                try:
                    # Get current market data (mock for now)
                    for symbol in symbols:
                        for timeframe in timeframes:
                            market_data = await self._get_current_market_data(symbol, timeframe)
                            
                            if market_data:
                                # Execute strategies
                                signals = await self.strategy_manager.execute_strategies(market_data)
                                
                                # Process signals
                                for signal in signals:
                                    context = {
                                        'current_volume': market_data.volume,
                                        'avg_volume': 1000.0  # Mock average volume
                                    }
                                    await self.signal_processor.process_signal(signal, context)
                    
                    # Cleanup expired signals
                    self.signal_processor.cleanup_expired_signals()
                    
                    # Wait before next iteration
                    await asyncio.sleep(60)  # Process every minute
                    
                except Exception as e:
                    logger.error(f"Real-time processing error: {e}")
                    await asyncio.sleep(5)  # Short delay on error
        
        self.processing_task = asyncio.create_task(processing_loop())
        logger.info(f"Real-time processing started for {len(symbols)} symbols")
    
    def stop_real_time_processing(self):
        """Stop real-time strategy processing"""
        self.real_time_enabled = False
        
        if self.processing_task:
            self.processing_task.cancel()
            self.processing_task = None
        
        logger.info("Real-time processing stopped")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'strategy_manager': self.strategy_manager.get_manager_status(),
            'signal_processor': self.signal_processor.get_signal_statistics(),
            'real_time_enabled': self.real_time_enabled,
            'available_templates': len(self.config_manager.templates),
            'performance_analyzer': {
                'strategies_tracked': len(self.performance_analyzer.trade_history),
                'total_trades_analyzed': sum(len(trades) for trades in self.performance_analyzer.trade_history.values())
            }
        }
    
    async def export_strategy_portfolio(self, strategy_ids: List[str], 
                                       filename: str = "strategy_portfolio.json") -> bool:
        """
        Export strategy portfolio configuration
        
        Args:
            strategy_ids: List of strategy IDs to export
            filename: Export filename
            
        Returns:
            True if exported successfully
        """
        try:
            portfolio = {
                'export_date': datetime.now().isoformat(),
                'strategies': []
            }
            
            for strategy_id in strategy_ids:
                strategy = self.strategy_manager.get_strategy(strategy_id)
                if strategy:
                    config_dict = {
                        'name': strategy.config.name,
                        'strategy_type': strategy.config.strategy_type.value,
                        'timeframe': strategy.config.timeframe,
                        'symbols': strategy.config.symbols,
                        'parameters': strategy.config.parameters,
                        'risk_settings': {
                            'max_position_size': strategy.config.max_position_size,
                            'stop_loss_pct': strategy.config.stop_loss_pct,
                            'take_profit_pct': strategy.config.take_profit_pct,
                            'trailing_stop': strategy.config.trailing_stop
                        },
                        'performance': strategy.get_status()['performance']
                    }
                    portfolio['strategies'].append(config_dict)
            
            export_path = self.data_dir / filename
            with open(export_path, 'w') as f:
                json.dump(portfolio, f, indent=2)
            
            logger.info(f"Portfolio exported: {len(portfolio['strategies'])} strategies to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export portfolio: {e}")
            return False
    
    async def import_strategy_portfolio(self, filename: str) -> Dict[str, Any]:
        """
        Import strategy portfolio configuration
        
        Args:
            filename: Import filename
            
        Returns:
            Import results
        """
        try:
            import_path = self.data_dir / filename
            
            if not import_path.exists():
                raise FileNotFoundError(f"Portfolio file not found: {import_path}")
            
            with open(import_path, 'r') as f:
                portfolio = json.load(f)
            
            imported_strategies = []
            failed_imports = []
            
            for strategy_config in portfolio['strategies']:
                try:
                    # Create strategy configuration
                    config = StrategyConfig(
                        name=f"imported_{strategy_config['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        strategy_type=StrategyType(strategy_config['strategy_type']),
                        timeframe=strategy_config['timeframe'],
                        symbols=strategy_config['symbols'],
                        parameters=strategy_config['parameters'],
                        **strategy_config['risk_settings']
                    )
                    
                    # Create strategy
                    strategy_id = self.strategy_manager.create_strategy(config)
                    imported_strategies.append(strategy_id)
                    
                except Exception as e:
                    failed_imports.append({
                        'name': strategy_config.get('name', 'unknown'),
                        'error': str(e)
                    })
            
            result = {
                'imported_strategies': len(imported_strategies),
                'failed_imports': len(failed_imports),
                'strategy_ids': imported_strategies,
                'failures': failed_imports
            }
            
            logger.info(f"Portfolio imported: {len(imported_strategies)} strategies, {len(failed_imports)} failures")
            return result
            
        except Exception as e:
            logger.error(f"Failed to import portfolio: {e}")
            return {'error': str(e)}
    
    def _simulate_trade(self, signal: Signal, market_data: MarketData, 
                       balance: float, positions: Dict, config: BacktestConfig) -> Optional[Dict[str, Any]]:
        """Simulate trade execution for backtesting"""
        symbol = signal.symbol
        
        if signal.action.value == 'buy':
            # Calculate position size (10% of balance for simplicity)
            position_value = balance * 0.1
            quantity = position_value / signal.price
            
            # Apply slippage and commission
            execution_price = signal.price * (1 + config.slippage_rate)
            commission = position_value * config.commission_rate
            
            # Check if we can afford the trade
            total_cost = (quantity * execution_price) + commission
            if total_cost <= balance:
                positions[symbol] = {
                    'quantity': quantity,
                    'entry_price': execution_price,
                    'entry_time': market_data.timestamp
                }
                
                trade = TradeAnalysis(
                    entry_time=market_data.timestamp,
                    exit_time=None,
                    symbol=symbol,
                    side='buy',
                    entry_price=execution_price,
                    exit_price=None,
                    quantity=quantity,
                    pnl=None,
                    pnl_pct=None,
                    duration_hours=None,
                    fees=commission,
                    signal_reason=signal.reason
                )
                
                return {
                    'pnl': -total_cost,
                    'quantity': quantity,
                    'trade': trade
                }
        
        elif signal.action.value == 'sell' and symbol in positions:
            position = positions[symbol]
            quantity = position['quantity']
            entry_price = position['entry_price']
            
            # Apply slippage and commission
            execution_price = signal.price * (1 - config.slippage_rate)
            commission = (quantity * execution_price) * config.commission_rate
            
            # Calculate PnL
            gross_pnl = (execution_price - entry_price) * quantity
            net_pnl = gross_pnl - commission
            pnl_pct = (net_pnl / (entry_price * quantity)) * 100
            
            # Calculate duration
            duration = market_data.timestamp - position['entry_time']
            duration_hours = duration.total_seconds() / 3600
            
            trade = TradeAnalysis(
                entry_time=position['entry_time'],
                exit_time=market_data.timestamp,
                symbol=symbol,
                side='sell',
                entry_price=entry_price,
                exit_price=execution_price,
                quantity=quantity,
                pnl=net_pnl,
                pnl_pct=pnl_pct,
                duration_hours=duration_hours,
                fees=commission,
                signal_reason=signal.reason
            )
            
            # Remove position
            del positions[symbol]
            
            return {
                'pnl': (quantity * execution_price) - commission,
                'quantity': quantity,
                'trade': trade
            }
        
        return None
    
    async def _get_historical_data(self, config: BacktestConfig) -> List[MarketData]:
        """Get historical market data for backtesting"""
        # This is a mock implementation
        # In real implementation, this would fetch from ccxt-gateway
        
        historical_data = []
        current_time = config.start_date
        
        while current_time < config.end_date:
            for symbol in config.symbols:
                for timeframe in config.timeframes:
                    market_data = MarketData(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=current_time,
                        open=50000.0,
                        high=50500.0,
                        low=49500.0,
                        close=50200.0,
                        volume=1000.0,
                        indicators={
                            'rsi': 45.0,
                            'ema12': 50100.0,
                            'ema26': 50000.0,
                            'macd': 100.0,
                            'macdSignal': 90.0,
                            'macdHist': 10.0
                        }
                    )
                    historical_data.append(market_data)
            
            # Increment time based on timeframe
            current_time += timedelta(hours=1)  # Simplified
        
        return historical_data
    
    async def _get_current_market_data(self, symbol: str, timeframe: str) -> Optional[MarketData]:
        """Get current market data"""
        # Mock implementation
        return MarketData(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(),
            open=50000.0,
            high=50200.0,
            low=49800.0,
            close=50100.0,
            volume=1200.0,
            indicators={
                'rsi': 52.0,
                'ema12': 50150.0,
                'ema26': 50050.0,
                'macd': 50.0,
                'macdSignal': 45.0,
                'macdHist': 5.0
            }
        )
    
    def _generate_performance_chart(self, balance_history: List[Dict]) -> Dict[str, Any]:
        """Generate performance chart data"""
        return {
            'type': 'line',
            'data': {
                'labels': [point['timestamp'].isoformat() for point in balance_history[-100:]],
                'datasets': [{
                    'label': 'Portfolio Balance',
                    'data': [point['balance'] for point in balance_history[-100:]],
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)'
                }]
            }
        }
    
    def _generate_strategy_recommendations(self, backtest_result: BacktestResult) -> List[str]:
        """Generate strategy improvement recommendations"""
        recommendations = []
        
        if backtest_result.win_rate < 40:
            recommendations.append("Consider tightening entry criteria or adding confirmation indicators")
        
        if backtest_result.max_drawdown_pct > 20:
            recommendations.append("Implement stricter risk management or position sizing")
        
        if backtest_result.total_trades < 10:
            recommendations.append("Strategy may be too conservative - consider relaxing entry criteria")
        
        if backtest_result.sharpe_ratio < 1.0:
            recommendations.append("Risk-adjusted returns are low - optimize risk/reward ratio")
        
        return recommendations