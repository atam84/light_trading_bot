# src/strategies/factory.py

from typing import Dict, List, Optional, Any, Type
import logging
from datetime import datetime

from .base import BaseStrategy, StrategyConfig, StrategyType
from .manager import StrategyManager
from .config import StrategyConfigManager, StrategyTemplate
from .simple import BuyLowSellHighStrategy, DCAStrategy, VolatilityBreakoutStrategy
from .grid import GridTradingStrategy
from .indicators import RSIStrategy, MovingAverageCrossStrategy, MACDStrategy, ComboIndicatorStrategy

logger = logging.getLogger(__name__)

class StrategyFactory:
    """
    Factory class for creating and managing strategy instances
    """
    
    def __init__(self):
        self.strategy_manager = StrategyManager()
        self.config_manager = StrategyConfigManager()
        
        # Quick strategy creation templates
        self.quick_templates = {
            'conservative': {
                'strategy_class': 'dca',
                'buy_amount': 25.0,
                'buy_interval_minutes': 120,
                'sell_trigger_pct': 15.0
            },
            'aggressive': {
                'strategy_class': 'rsi',
                'rsi_period': 7,
                'oversold_threshold': 25,
                'overbought_threshold': 75
            },
            'balanced': {
                'strategy_class': 'combo_indicator',
                'entry_indicators': ['rsi', 'ma_cross'],
                'rsi_oversold': 35,
                'rsi_overbought': 65
            },
            'scalping': {
                'strategy_class': 'volatility_breakout',
                'volume_multiplier': 3.0,
                'price_change_pct': 2.0,
                'lookback_periods': 10
            },
            'grid_stable': {
                'strategy_class': 'grid_trading',
                'grid_levels': 15,
                'grid_spacing_pct': 0.5,
                'base_amount_usd': 50.0
            }
        }
        
        logger.info("Strategy factory initialized")
    
    def create_quick_strategy(self, profile: str, symbol: str, timeframe: str = "1h",
                            budget_per_trade: float = 100.0) -> str:
        """
        Create a strategy using predefined profiles
        
        Args:
            profile: Strategy profile ('conservative', 'aggressive', 'balanced', etc.)
            symbol: Trading symbol
            timeframe: Trading timeframe
            budget_per_trade: Budget per trade in USD
            
        Returns:
            Strategy ID
        """
        if profile not in self.quick_templates:
            raise ValueError(f"Unknown profile: {profile}. Available: {list(self.quick_templates.keys())}")
        
        # Get template parameters
        template_params = self.quick_templates[profile].copy()
        strategy_class = template_params.pop('strategy_class')
        
        # Adjust budget-related parameters
        if 'buy_amount' in template_params:
            template_params['buy_amount'] = min(template_params['buy_amount'], budget_per_trade)
        if 'base_amount_usd' in template_params:
            template_params['base_amount_usd'] = min(template_params['base_amount_usd'], budget_per_trade)
        
        # Add strategy class to parameters
        template_params['strategy_class'] = strategy_class
        
        # Create strategy name
        strategy_name = f"{profile}_{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create configuration
        config = StrategyConfig(
            name=strategy_name,
            strategy_type=StrategyType.SIMPLE if strategy_class in ['dca', 'buy_low_sell_high'] else StrategyType.INDICATOR,
            timeframe=timeframe,
            symbols=[symbol],
            max_position_size=budget_per_trade,
            parameters=template_params
        )
        
        # Create strategy
        strategy_id = self.strategy_manager.create_strategy(config)
        
        logger.info(f"Quick strategy created: {strategy_id} (profile: {profile})")
        return strategy_id
    
    def create_custom_strategy(self, name: str, strategy_type: str, symbol: str,
                             timeframe: str = "1h", parameters: Optional[Dict[str, Any]] = None,
                             risk_settings: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a custom strategy with specific parameters
        
        Args:
            name: Strategy name
            strategy_type: Strategy type or class name
            symbol: Trading symbol
            timeframe: Trading timeframe
            parameters: Strategy-specific parameters
            risk_settings: Risk management settings
            
        Returns:
            Strategy ID
        """
        # Determine strategy type enum
        if strategy_type in ['simple', 'dca', 'buy_low_sell_high']:
            strategy_enum = StrategyType.SIMPLE
        elif strategy_type in ['grid', 'grid_trading']:
            strategy_enum = StrategyType.GRID
        elif strategy_type in ['indicator', 'rsi', 'macd', 'ma_cross', 'combo']:
            strategy_enum = StrategyType.INDICATOR
        else:
            strategy_enum = StrategyType.CUSTOM
        
        # Default parameters
        if parameters is None:
            parameters = {}
        
        # Add strategy class if not specified
        if 'strategy_class' not in parameters:
            parameters['strategy_class'] = strategy_type
        
        # Default risk settings
        default_risk = {
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.15,
            'max_position_size': 100.0,
            'trailing_stop': False
        }
        
        if risk_settings:
            default_risk.update(risk_settings)
        
        # Create configuration
        config = StrategyConfig(
            name=name,
            strategy_type=strategy_enum,
            timeframe=timeframe,
            symbols=[symbol],
            parameters=parameters,
            **default_risk
        )
        
        # Create strategy
        strategy_id = self.strategy_manager.create_strategy(config)
        
        logger.info(f"Custom strategy created: {strategy_id}")
        return strategy_id
    
    def create_from_template(self, template_name: str, name: str, symbol: str,
                           timeframe: str = "1h", overrides: Optional[Dict[str, Any]] = None) -> str:
        """
        Create strategy from predefined template
        
        Args:
            template_name: Template name
            name: Strategy instance name
            symbol: Trading symbol
            timeframe: Trading timeframe
            overrides: Parameter overrides
            
        Returns:
            Strategy ID
        """
        # Create config from template
        config = self.config_manager.create_config_from_template(
            template_name=template_name,
            config_name=name,
            symbol=symbol,
            timeframe=timeframe,
            custom_parameters=overrides
        )
        
        # Create strategy
        strategy_id = self.strategy_manager.create_strategy(config)
        
        logger.info(f"Strategy created from template '{template_name}': {strategy_id}")
        return strategy_id
    
    def clone_strategy(self, existing_strategy_id: str, new_name: str, 
                      symbol: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> str:
        """
        Clone an existing strategy with optional modifications
        
        Args:
            existing_strategy_id: ID of strategy to clone
            new_name: Name for cloned strategy
            symbol: New symbol (optional)
            overrides: Parameter overrides
            
        Returns:
            New strategy ID
        """
        existing_strategy = self.strategy_manager.get_strategy(existing_strategy_id)
        if not existing_strategy:
            raise ValueError(f"Strategy '{existing_strategy_id}' not found")
        
        # Copy configuration
        old_config = existing_strategy.config
        new_parameters = old_config.parameters.copy()
        
        if overrides:
            new_parameters.update(overrides)
        
        # Create new configuration
        new_config = StrategyConfig(
            name=new_name,
            strategy_type=old_config.strategy_type,
            timeframe=old_config.timeframe,
            symbols=[symbol] if symbol else old_config.symbols.copy(),
            active=old_config.active,
            max_position_size=old_config.max_position_size,
            stop_loss_pct=old_config.stop_loss_pct,
            take_profit_pct=old_config.take_profit_pct,
            trailing_stop=old_config.trailing_stop,
            parameters=new_parameters
        )
        
        # Create cloned strategy
        strategy_id = self.strategy_manager.create_strategy(new_config)
        
        logger.info(f"Strategy cloned: {existing_strategy_id} -> {strategy_id}")
        return strategy_id
    
    def create_portfolio_strategies(self, symbols: List[str], profile: str = "balanced",
                                  timeframe: str = "4h", total_budget: float = 1000.0) -> List[str]:
        """
        Create multiple strategies for a portfolio of symbols
        
        Args:
            symbols: List of trading symbols
            profile: Strategy profile to use
            timeframe: Trading timeframe
            total_budget: Total budget to distribute
            
        Returns:
            List of strategy IDs
        """
        budget_per_symbol = total_budget / len(symbols)
        strategy_ids = []
        
        for symbol in symbols:
            try:
                strategy_id = self.create_quick_strategy(
                    profile=profile,
                    symbol=symbol,
                    timeframe=timeframe,
                    budget_per_trade=budget_per_symbol
                )
                strategy_ids.append(strategy_id)
                
            except Exception as e:
                logger.error(f"Failed to create strategy for {symbol}: {e}")
        
        logger.info(f"Portfolio strategies created: {len(strategy_ids)} strategies for {len(symbols)} symbols")
        return strategy_ids
    
    def get_strategy_recommendations(self, symbol: str, timeframe: str,
                                   risk_tolerance: str = "medium",
                                   trading_style: str = "swing") -> List[Dict[str, Any]]:
        """
        Get strategy recommendations based on preferences
        
        Args:
            symbol: Trading symbol
            timeframe: Trading timeframe
            risk_tolerance: 'low', 'medium', 'high'
            trading_style: 'scalping', 'day', 'swing', 'position'
            
        Returns:
            List of recommended strategies
        """
        recommendations = []
        
        # Map risk tolerance to profiles
        risk_profiles = {
            'low': ['conservative', 'balanced'],
            'medium': ['balanced', 'grid_stable'],
            'high': ['aggressive', 'scalping']
        }
        
        # Map trading style to timeframes and strategies
        style_strategies = {
            'scalping': {
                'timeframes': ['1m', '5m', '15m'],
                'strategies': ['volatility_breakout', 'grid_trading']
            },
            'day': {
                'timeframes': ['15m', '1h'],
                'strategies': ['rsi', 'ma_cross', 'volatility_breakout']
            },
            'swing': {
                'timeframes': ['4h', '1d'],
                'strategies': ['combo_indicator', 'macd', 'buy_low_sell_high']
            },
            'position': {
                'timeframes': ['1d', '1w'],
                'strategies': ['dca', 'ma_cross', 'buy_low_sell_high']
            }
        }
        
        # Get suitable profiles
        suitable_profiles = risk_profiles.get(risk_tolerance, ['balanced'])
        
        # Get style-specific strategies
        style_info = style_strategies.get(trading_style, style_strategies['swing'])
        
        # Check if timeframe matches style
        timeframe_match = timeframe in style_info['timeframes']
        
        for profile in suitable_profiles:
            template_params = self.quick_templates[profile].copy()
            strategy_class = template_params['strategy_class']
            
            # Calculate compatibility score
            score = 0.5  # Base score
            
            if timeframe_match:
                score += 0.3
            
            if strategy_class in style_info['strategies']:
                score += 0.2
            
            recommendations.append({
                'profile': profile,
                'strategy_class': strategy_class,
                'compatibility_score': score,
                'description': self._get_strategy_description(profile, strategy_class),
                'risk_level': self._get_risk_level(profile),
                'parameters': template_params
            })
        
        # Sort by compatibility score
        recommendations.sort(key=lambda x: x['compatibility_score'], reverse=True)
        
        return recommendations
    
    def optimize_strategy_parameters(self, strategy_id: str, optimization_metric: str = "sharpe_ratio",
                                   parameter_ranges: Optional[Dict[str, tuple]] = None) -> Dict[str, Any]:
        """
        Suggest optimized parameters for a strategy
        
        Args:
            strategy_id: Strategy to optimize
            optimization_metric: Metric to optimize for
            parameter_ranges: Parameter ranges to test
            
        Returns:
            Optimization results
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy '{strategy_id}' not found")
        
        current_params = strategy.config.parameters.copy()
        optimization_suggestions = {}
        
        # Default parameter ranges for optimization
        default_ranges = {
            'rsi_period': (7, 21),
            'oversold_threshold': (20, 40),
            'overbought_threshold': (60, 80),
            'fast_period': (5, 20),
            'slow_period': (15, 50),
            'grid_spacing_pct': (0.5, 3.0),
            'buy_threshold_pct': (2.0, 10.0),
            'sell_threshold_pct': (5.0, 25.0)
        }
        
        if parameter_ranges:
            default_ranges.update(parameter_ranges)
        
        # Analyze current performance
        performance = strategy.performance_metrics
        current_win_rate = performance.get('win_rate', 0)
        current_total_pnl = performance.get('total_pnl', 0)
        
        # Generate optimization suggestions
        for param, (min_val, max_val) in default_ranges.items():
            if param in current_params:
                current_val = current_params[param]
                
                # Simple optimization logic based on performance
                if current_win_rate < 40:  # Low win rate
                    if 'threshold' in param:
                        # Make thresholds more conservative
                        suggested_val = current_val * 0.8 if 'oversold' in param or 'buy' in param else current_val * 1.2
                    else:
                        suggested_val = current_val
                elif current_win_rate > 70:  # High win rate, be more aggressive
                    if 'threshold' in param:
                        suggested_val = current_val * 1.2 if 'oversold' in param or 'buy' in param else current_val * 0.8
                    else:
                        suggested_val = current_val
                else:
                    suggested_val = current_val  # Keep current
                
                # Ensure within bounds
                suggested_val = max(min_val, min(max_val, suggested_val))
                
                if abs(suggested_val - current_val) > 0.1:  # Only suggest if significant change
                    optimization_suggestions[param] = {
                        'current': current_val,
                        'suggested': round(suggested_val, 2),
                        'reason': self._get_optimization_reason(param, current_val, suggested_val, current_win_rate)
                    }
        
        return {
            'strategy_id': strategy_id,
            'current_performance': performance,
            'optimization_metric': optimization_metric,
            'parameter_suggestions': optimization_suggestions,
            'improvement_potential': len(optimization_suggestions) > 0
        }
    
    def _get_strategy_description(self, profile: str, strategy_class: str) -> str:
        """Get description for strategy profile"""
        descriptions = {
            'conservative': "Low-risk strategy with steady, gradual accumulation",
            'aggressive': "High-frequency trading with quick entries and exits",
            'balanced': "Moderate risk with multiple confirmation signals",
            'scalping': "High-frequency trades on short-term volatility",
            'grid_stable': "Automated grid trading for stable markets"
        }
        return descriptions.get(profile, f"Strategy using {strategy_class} approach")
    
    def _get_risk_level(self, profile: str) -> str:
        """Get risk level for profile"""
        risk_levels = {
            'conservative': 'low',
            'balanced': 'medium',
            'aggressive': 'high',
            'scalping': 'high',
            'grid_stable': 'medium'
        }
        return risk_levels.get(profile, 'medium')
    
    def _get_optimization_reason(self, param: str, current_val: float, 
                                suggested_val: float, win_rate: float) -> str:
        """Get reason for parameter optimization suggestion"""
        if win_rate < 40:
            return f"Low win rate ({win_rate:.1f}%) suggests more conservative {param}"
        elif win_rate > 70:
            return f"High win rate ({win_rate:.1f}%) allows for more aggressive {param}"
        else:
            return f"Moderate adjustment to improve {param} effectiveness"
    
    def get_factory_status(self) -> Dict[str, Any]:
        """
        Get factory status and statistics
        
        Returns:
            Factory status information
        """
        return {
            'available_profiles': list(self.quick_templates.keys()),
            'available_templates': len(self.config_manager.templates),
            'strategy_manager_status': self.strategy_manager.get_manager_status(),
            'total_strategies_created': len(self.strategy_manager.strategies)
        }