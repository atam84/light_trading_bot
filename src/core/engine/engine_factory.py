# src/core/engine/engine_factory.py

import asyncio
import logging
from typing import Dict, Any, Optional, Type
from datetime import datetime

# Import all core components
from .trading_engine import TradingEngine, TradingMode
from .mode_manager import ModeManager
from ..strategies.base_strategy import StrategyManager, BaseStrategy
from ..risk.risk_manager import RiskManager
from ..orders.order_manager import OrderManager
from ..data.data_manager import DataManager
from ..config.config_manager import ConfigManager

class EngineFactory:
    """Factory for creating and configuring trading engine instances"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    async def create_engine(self, engine_name: str = "default", 
                          trading_mode: TradingMode = TradingMode.PAPER) -> Optional[TradingEngine]:
        """Create a fully configured trading engine"""
        try:
            self.logger.info(f"Creating trading engine: {engine_name}")
            
            # Get configuration
            engine_config = self._build_engine_config(engine_name)
            
            # Create core engine
            engine = TradingEngine(engine_config)
            
            # Create and inject all components
            components = await self._create_components(engine_config)
            
            # Inject components into engine
            engine.set_mode_manager(components['mode_manager'])
            engine.set_strategy_manager(components['strategy_manager'])
            engine.set_risk_manager(components['risk_manager'])
            engine.set_order_manager(components['order_manager'])
            engine.set_data_manager(components['data_manager'])
            
            # Set up component dependencies
            await self._setup_component_dependencies(components)
            
            # Initialize engine
            if not await engine.initialize(trading_mode):
                raise Exception("Failed to initialize trading engine")
            
            self.logger.info(f"Trading engine {engine_name} created successfully")
            return engine
            
        except Exception as e:
            self.logger.error(f"Failed to create trading engine {engine_name}: {e}")
            return None
    
    def _build_engine_config(self, engine_name: str) -> Dict[str, Any]:
        """Build engine configuration from config manager"""
        return {
            'name': engine_name,
            'mode': self.config_manager.get('trading.mode', 'paper'),
            'trading': self.config_manager.get_section('trading'),
            'risk_management': self.config_manager.get_section('risk_management'),
            'data': self.config_manager.get_section('data'),
            'strategies': self.config_manager.get_section('strategies')
        }
    
    async def _create_components(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create all engine components"""
        components = {}
        
        # Create mode manager
        mode_config = {
            'live': config.get('live_trading', {}),
            'paper': config.get('paper_trading', {
                'initial_balance': 10000.0,
                'fee_rate': 0.0005,
                'slippage': 0.0002
            }),
            'backtest': config.get('backtesting', {
                'initial_balance': 10000.0,
                'fee_rate': 0.0005,
                'slippage': 0.0002
            })
        }
        components['mode_manager'] = ModeManager(mode_config)
        
        # Create risk manager
        components['risk_manager'] = RiskManager(config)
        
        # Create order manager
        order_config = config.get('orders', {
            'max_concurrent_executions': 5,
            'execution_timeout': 30,
            'retry_delay': 5
        })
        components['order_manager'] = OrderManager(order_config)
        
        # Create data manager
        data_config = config.get('data', {})
        components['data_manager'] = DataManager(data_config)
        
        # Create strategy manager
        components['strategy_manager'] = StrategyManager(config)
        
        self.logger.info("All engine components created")
        return components
    
    async def _setup_component_dependencies(self, components: Dict[str, Any]):
        """Set up dependencies between components"""
        # Order manager needs mode manager for execution
        components['order_manager'].set_mode_manager(components['mode_manager'])
        
        # Initialize all components
        for name, component in components.items():
            if hasattr(component, 'initialize'):
                success = await component.initialize()
                if not success:
                    raise Exception(f"Failed to initialize component: {name}")
        
        self.logger.info("Component dependencies configured")


# Integration testing framework
class CoreIntegrationTest:
    """Integration test suite for core engine components"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.test_results = []
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        self.logger.info("Starting core integration tests")
        
        test_methods = [
            self._test_config_manager,
            self._test_data_manager,
            self._test_risk_manager,
            self._test_order_manager,
            self._test_strategy_manager,
            self._test_mode_manager,
            self._test_engine_factory,
            self._test_full_engine_lifecycle
        ]
        
        total_tests = len(test_methods)
        passed_tests = 0
        
        for test_method in test_methods:
            try:
                result = await test_method()
                if result:
                    passed_tests += 1
                    self.logger.info(f"✅ {test_method.__name__} PASSED")
                else:
                    self.logger.error(f"❌ {test_method.__name__} FAILED")
                    
            except Exception as e:
                self.logger.error(f"❌ {test_method.__name__} ERROR: {e}")
        
        success_rate = (passed_tests / total_tests) * 100
        
        results = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': success_rate,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"Integration tests completed: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
        return results
    
    async def _test_config_manager(self) -> bool:
        """Test configuration manager"""
        try:
            config_manager = ConfigManager("test_config")
            
            # Test initialization
            assert await config_manager.initialize(), "Config manager initialization failed"
            
            # Test setting and getting values
            await config_manager.set("test.key", "test_value")
            value = config_manager.get("test.key")
            assert value == "test_value", "Config set/get failed"
            
            # Test validation
            from ..config.config_manager import ConfigRule
            config_manager.add_validation_rule(ConfigRule(
                key="test.number",
                rule_type="type",
                description="Test number",
                rule_data=int,
                error_message="Must be integer"
            ))
            
            success = await config_manager.set("test.number", "not_a_number")
            assert not success, "Validation should have failed"
            
            await config_manager.cleanup()
            return True
            
        except Exception as e:
            self.logger.error(f"Config manager test failed: {e}")
            return False
    
    async def _test_data_manager(self) -> bool:
        """Test data manager"""
        try:
            config = {
                'ccxt_gateway_url': 'http://localhost:3000',
                'cache_enabled': True,
                'default_cache_ttl': 300
            }
            
            data_manager = DataManager(config)
            
            # Test initialization (may fail if ccxt-gateway not available)
            # We'll test the basic functionality without actual API calls
            
            # Test cache functionality
            from ..data.data_manager import MarketDataPoint
            test_data = [
                MarketDataPoint(
                    symbol="BTC/USDT",
                    timestamp=datetime.utcnow(),
                    open=45000.0,
                    high=45500.0,
                    low=44500.0,
                    close=45200.0,
                    volume=100.0,
                    timeframe="1h"
                )
            ]
            
            data_manager._add_to_cache("test_key", test_data)
            cached_data = data_manager._get_from_cache("test_key")
            
            assert cached_data is not None, "Cache store/retrieve failed"
            assert len(cached_data) == 1, "Cached data length mismatch"
            
            await data_manager.cleanup()
            return True
            
        except Exception as e:
            self.logger.error(f"Data manager test failed: {e}")
            return False
    
    async def _test_risk_manager(self) -> bool:
        """Test risk manager"""
        try:
            config = {
                'risk_management': {
                    'max_allocation_percentage': 0.5,
                    'max_trade_amount': 1000.0,
                    'max_positions': 10
                }
            }
            
            risk_manager = RiskManager(config)
            
            # Test trade validation
            from ..risk.risk_manager import TradeValidationRequest
            request = TradeValidationRequest(
                symbol="BTC/USDT",
                side="buy",
                amount=0.01,
                price=45000.0,
                strategy_name="test_strategy"
            )
            
            result = await risk_manager.validate_trade(request)
            assert result.is_valid, "Valid trade should be approved"
            
            # Test emergency stop
            await risk_manager.trigger_emergency_stop("Test emergency")
            assert risk_manager.is_emergency_stop_active(), "Emergency stop should be active"
            
            # Test validation with emergency stop
            result = await risk_manager.validate_trade(request)
            assert not result.is_valid, "Trade should be blocked during emergency stop"
            
            await risk_manager.cleanup()
            return True
            
        except Exception as e:
            self.logger.error(f"Risk manager test failed: {e}")
            return False
    
    async def _test_order_manager(self) -> bool:
        """Test order manager"""
        try:
            config = {
                'max_concurrent_executions': 2,
                'execution_timeout': 30,
                'retry_delay': 1
            }
            
            order_manager = OrderManager(config)
            
            # Test initialization
            assert await order_manager.initialize(), "Order manager initialization failed"
            
            # Test order creation and submission
            from ..orders.order_manager import Order, OrderSide, OrderType
            order = Order(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                amount=0.01,
                strategy_name="test_strategy"
            )
            
            # Submit order (will fail without mode manager, but tests validation)
            submitted = await order_manager.submit_order(order)
            assert order.order_id in order_manager._orders, "Order should be stored"
            
            # Test order retrieval
            retrieved_order = order_manager.get_order(order.order_id)
            assert retrieved_order is not None, "Order retrieval failed"
            
            # Test order cancellation
            cancelled = await order_manager.cancel_order(order.order_id)
            
            await order_manager.cleanup()
            return True
            
        except Exception as e:
            self.logger.error(f"Order manager test failed: {e}")
            return False
    
    async def _test_strategy_manager(self) -> bool:
        """Test strategy manager"""
        try:
            config = {}
            strategy_manager = StrategyManager(config)
            
            # Create a simple test strategy
            class TestStrategy(BaseStrategy):
                async def analyze_market(self, symbol, market_data):
                    from ..strategies.base_strategy import TradingSignal, SignalType
                    return TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.HOLD,
                        price=45000.0
                    )
                
                def validate_parameters(self):
                    return True
                
                def get_required_indicators(self):
                    return []
            
            # Test strategy addition
            test_strategy = TestStrategy({'name': 'test_strategy'})
            assert strategy_manager.add_strategy(test_strategy), "Strategy addition failed"
            
            # Test strategy activation
            assert await strategy_manager.activate_strategy('test_strategy'), "Strategy activation failed"
            
            # Test strategy processing
            signals = await strategy_manager.process_cycle({})
            assert isinstance(signals, list), "Strategy processing should return list"
            
            await strategy_manager.cleanup()
            return True
            
        except Exception as e:
            self.logger.error(f"Strategy manager test failed: {e}")
            return False
    
    async def _test_mode_manager(self) -> bool:
        """Test mode manager"""
        try:
            config = {
                'paper': {
                    'initial_balance': 10000.0,
                    'fee_rate': 0.0005
                },
                'backtest': {
                    'initial_balance': 10000.0,
                    'start_date': '2024-01-01',
                    'end_date': '2024-01-31'
                }
            }
            
            mode_manager = ModeManager(config)
            
            # Test mode switching
            assert await mode_manager.set_mode(TradingMode.PAPER), "Failed to set paper mode"
            assert mode_manager.get_mode_type() == TradingMode.PAPER, "Mode type mismatch"
            
            # Test mode execution
            current_mode = mode_manager.get_current_mode()
            assert current_mode is not None, "No current mode set"
            
            # Test paper trade execution
            result = await current_mode.execute_trade("BTC/USDT", "buy", 0.01, 45000.0)
            assert result is not None, "Trade execution failed"
            assert 'id' in result, "Trade result missing ID"
            
            await mode_manager.cleanup()
            return True
            
        except Exception as e:
            self.logger.error(f"Mode manager test failed: {e}")
            return False
    
    async def _test_engine_factory(self) -> bool:
        """Test engine factory"""
        try:
            # Create test config manager
            config_manager = ConfigManager("test_config")
            await config_manager.initialize()
            
            # Create engine factory
            factory = EngineFactory(config_manager)
            
            # Test engine creation
            engine = await factory.create_engine("test_engine", TradingMode.PAPER)
            assert engine is not None, "Engine creation failed"
            
            # Test engine components
            assert engine.mode_manager is not None, "Mode manager not injected"
            assert engine.strategy_manager is not None, "Strategy manager not injected"
            assert engine.risk_manager is not None, "Risk manager not injected"
            assert engine.order_manager is not None, "Order manager not injected"
            assert engine.data_manager is not None, "Data manager not injected"
            
            # Test engine health
            assert engine.is_healthy(), "Engine should be healthy"
            
            await engine.cleanup()
            await config_manager.cleanup()
            return True
            
        except Exception as e:
            self.logger.error(f"Engine factory test failed: {e}")
            return False
    
    async def _test_full_engine_lifecycle(self) -> bool:
        """Test full engine lifecycle"""
        try:
            # Create and configure engine
            config_manager = ConfigManager("test_config")
            await config_manager.initialize()
            
            factory = EngineFactory(config_manager)
            engine = await factory.create_engine("lifecycle_test", TradingMode.PAPER)
            
            assert engine is not None, "Engine creation failed"
            
            # Test engine start
            assert await engine.start(), "Engine start failed"
            assert engine.get_state().name == "RUNNING", "Engine should be running"
            
            # Let engine run for a brief moment
            await asyncio.sleep(0.5)
            
            # Test engine pause
            assert await engine.pause(), "Engine pause failed"
            assert engine.get_state().name == "PAUSED", "Engine should be paused"
            
            # Test engine resume
            assert await engine.resume(), "Engine resume failed"
            assert engine.get_state().name == "RUNNING", "Engine should be running"
            
            # Test engine stop
            assert await engine.stop(), "Engine stop failed"
            assert engine.get_state().name == "STOPPED", "Engine should be stopped"
            
            # Test engine status
            status = engine.get_status()
            assert isinstance(status.to_dict(), dict), "Status should be convertible to dict"
            
            await engine.cleanup()
            await config_manager.cleanup()
            return True
            
        except Exception as e:
            self.logger.error(f"Full engine lifecycle test failed: {e}")
            return False


# Utility functions for testing
async def run_integration_tests() -> Dict[str, Any]:
    """Run all integration tests"""
    test_suite = CoreIntegrationTest()
    return await test_suite.run_all_tests()

async def create_test_engine() -> Optional[TradingEngine]:
    """Create a test engine for development"""
    try:
        config_manager = ConfigManager("test_config")
        await config_manager.initialize()
        
        # Set test configuration
        await config_manager.set("trading.mode", "paper")
        await config_manager.set("data.ccxt_gateway_url", "http://localhost:3000")
        
        factory = EngineFactory(config_manager)
        engine = await factory.create_engine("test_engine", TradingMode.PAPER)
        
        return engine
        
    except Exception as e:
        logging.error(f"Failed to create test engine: {e}")
        return None

# Main integration module
class CoreIntegration:
    """Main integration point for all core components"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_manager = ConfigManager(config_dir)
        self.engine_factory = EngineFactory(self.config_manager)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self._engines: Dict[str, TradingEngine] = {}
    
    async def initialize(self) -> bool:
        """Initialize core integration"""
        try:
            # Initialize configuration
            if not await self.config_manager.initialize():
                raise Exception("Failed to initialize configuration manager")
            
            self.logger.info("Core integration initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core integration: {e}")
            return False
    
    async def create_engine(self, name: str, mode: TradingMode = TradingMode.PAPER) -> Optional[TradingEngine]:
        """Create and register a new engine"""
        try:
            engine = await self.engine_factory.create_engine(name, mode)
            if engine:
                self._engines[name] = engine
                self.logger.info(f"Engine {name} created and registered")
            return engine
            
        except Exception as e:
            self.logger.error(f"Failed to create engine {name}: {e}")
            return None
    
    def get_engine(self, name: str) -> Optional[TradingEngine]:
        """Get engine by name"""
        return self._engines.get(name)
    
    def get_all_engines(self) -> Dict[str, TradingEngine]:
        """Get all engines"""
        return self._engines.copy()
    
    async def start_engine(self, name: str) -> bool:
        """Start an engine"""
        engine = self._engines.get(name)
        if engine:
            return await engine.start()
        return False
    
    async def stop_engine(self, name: str) -> bool:
        """Stop an engine"""
        engine = self._engines.get(name)
        if engine:
            return await engine.stop()
        return False
    
    async def remove_engine(self, name: str) -> bool:
        """Remove an engine"""
        if name in self._engines:
            engine = self._engines[name]
            await engine.stop()
            await engine.cleanup()
            del self._engines[name]
            self.logger.info(f"Engine {name} removed")
            return True
        return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        engine_statuses = {}
        for name, engine in self._engines.items():
            engine_statuses[name] = {
                'state': engine.get_state().value,
                'mode': engine.mode_manager.get_mode_type().value if engine.mode_manager else 'unknown',
                'healthy': engine.is_healthy(),
                'uptime': engine.get_status().uptime_seconds
            }
        
        return {
            'config_manager': {
                'healthy': self.config_manager.is_healthy(),
                'status': self.config_manager.get_status()
            },
            'engines': engine_statuses,
            'total_engines': len(self._engines),
            'running_engines': sum(1 for engine in self._engines.values() 
                                 if engine.get_state().name == "RUNNING"),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        health_status = {
            'overall_healthy': True,
            'components': {},
            'engines': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check config manager
        config_healthy = self.config_manager.is_healthy()
        health_status['components']['config_manager'] = config_healthy
        if not config_healthy:
            health_status['overall_healthy'] = False
        
        # Check engines
        for name, engine in self._engines.items():
            engine_healthy = engine.is_healthy()
            health_status['engines'][name] = {
                'healthy': engine_healthy,
                'state': engine.get_state().value,
                'components': {
                    'mode_manager': engine.mode_manager.is_healthy() if engine.mode_manager else False,
                    'strategy_manager': engine.strategy_manager.is_healthy() if engine.strategy_manager else False,
                    'risk_manager': engine.risk_manager.is_healthy() if engine.risk_manager else False,
                    'order_manager': engine.order_manager.is_healthy() if engine.order_manager else False,
                    'data_manager': engine.data_manager.is_healthy() if engine.data_manager else False
                }
            }
            
            if not engine_healthy:
                health_status['overall_healthy'] = False
        
        return health_status
    
    async def cleanup(self):
        """Cleanup all components"""
        # Stop and cleanup all engines
        for name in list(self._engines.keys()):
            await self.remove_engine(name)
        
        # Cleanup config manager
        await self.config_manager.cleanup()
        
        self.logger.info("Core integration cleaned up")