# src/strategies/config.py

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import yaml
from pathlib import Path
import logging

from .base import StrategyConfig, StrategyType

logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Configuration validation error"""
    pass

@dataclass
class StrategyTemplate:
    """Strategy template with default parameters"""
    name: str
    strategy_type: StrategyType
    description: str
    default_parameters: Dict[str, Any]
    required_parameters: List[str] = field(default_factory=list)
    parameter_descriptions: Dict[str, str] = field(default_factory=dict)
    risk_level: str = "medium"  # low, medium, high
    recommended_timeframes: List[str] = field(default_factory=list)
    
class StrategyConfigManager:
    """
    Manages strategy configurations, templates, and validation
    """
    
    def __init__(self, config_dir: str = "configs/strategies"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.templates: Dict[str, StrategyTemplate] = {}
        self.saved_configs: Dict[str, StrategyConfig] = {}
        
        # Initialize default templates
        self._initialize_default_templates()
        
        # Load saved configurations
        self._load_saved_configs()
        
        logger.info(f"Strategy config manager initialized with {len(self.templates)} templates")
    
    def _initialize_default_templates(self):
        """Initialize default strategy templates"""
        
        # Buy Low Sell High Template
        self.templates['buy_low_sell_high'] = StrategyTemplate(
            name="Buy Low Sell High",
            strategy_type=StrategyType.SIMPLE,
            description="Simple strategy that buys when price drops significantly and sells for profit",
            default_parameters={
                'strategy_class': 'buy_low_sell_high',
                'buy_threshold_pct': 5.0,
                'sell_threshold_pct': 10.0,
                'lookback_hours': 24,
                'min_volume': 1000.0
            },
            required_parameters=['buy_threshold_pct', 'sell_threshold_pct'],
            parameter_descriptions={
                'buy_threshold_pct': 'Percentage below recent high to trigger buy signal',
                'sell_threshold_pct': 'Percentage above buy price to trigger sell signal',
                'lookback_hours': 'Hours to look back for high/low calculation',
                'min_volume': 'Minimum volume required for signal generation'
            },
            risk_level="medium",
            recommended_timeframes=['1h', '4h', '1d']
        )
        
        # DCA Template
        self.templates['dca'] = StrategyTemplate(
            name="Dollar Cost Averaging",
            strategy_type=StrategyType.SIMPLE,
            description="Buys fixed amount at regular intervals regardless of price",
            default_parameters={
                'strategy_class': 'dca',
                'buy_amount': 50.0,
                'buy_interval_minutes': 60,
                'sell_trigger_pct': 20.0,
                'max_positions': 5
            },
            required_parameters=['buy_amount', 'buy_interval_minutes'],
            parameter_descriptions={
                'buy_amount': 'Fixed USD amount to buy each interval',
                'buy_interval_minutes': 'Minutes between DCA purchases',
                'sell_trigger_pct': 'Percentage gain to trigger sell',
                'max_positions': 'Maximum number of DCA positions'
            },
            risk_level="low",
            recommended_timeframes=['1h', '4h']
        )
        
        # Grid Trading Template
        self.templates['grid_trading'] = StrategyTemplate(
            name="Grid Trading",
            strategy_type=StrategyType.GRID,
            description="Places buy and sell orders at regular price intervals",
            default_parameters={
                'strategy_class': 'grid_trading',
                'grid_levels': 10,
                'grid_spacing_pct': 1.0,
                'base_amount_usd': 100.0,
                'rebalance_threshold_pct': 5.0,
                'take_profit_pct': 1.5
            },
            required_parameters=['grid_levels', 'grid_spacing_pct', 'base_amount_usd'],
            parameter_descriptions={
                'grid_levels': 'Number of grid levels to create',
                'grid_spacing_pct': 'Percentage spacing between grid levels',
                'base_amount_usd': 'USD amount per grid level',
                'rebalance_threshold_pct': 'Rebalance grid when price moves this %',
                'take_profit_pct': 'Take profit percentage per trade'
            },
            risk_level="medium",
            recommended_timeframes=['15m', '1h', '4h']
        )
        
        # RSI Template
        self.templates['rsi'] = StrategyTemplate(
            name="RSI Strategy",
            strategy_type=StrategyType.INDICATOR,
            description="Trades based on RSI overbought/oversold levels",
            default_parameters={
                'strategy_class': 'rsi',
                'rsi_period': 14,
                'oversold_threshold': 30,
                'overbought_threshold': 70,
                'exit_rsi_middle': 50
            },
            required_parameters=['oversold_threshold', 'overbought_threshold'],
            parameter_descriptions={
                'rsi_period': 'RSI calculation period',
                'oversold_threshold': 'RSI level considered oversold (buy signal)',
                'overbought_threshold': 'RSI level considered overbought (sell signal)',
                'exit_rsi_middle': 'Exit when RSI returns to this level'
            },
            risk_level="medium",
            recommended_timeframes=['1h', '4h', '1d']
        )
        
        # Moving Average Cross Template
        self.templates['ma_cross'] = StrategyTemplate(
            name="MA Crossover",
            strategy_type=StrategyType.INDICATOR,
            description="Trades on moving average crossovers",
            default_parameters={
                'strategy_class': 'ma_cross',
                'fast_period': 12,
                'slow_period': 26,
                'ma_type': 'ema',
                'confirm_periods': 2
            },
            required_parameters=['fast_period', 'slow_period'],
            parameter_descriptions={
                'fast_period': 'Fast moving average period',
                'slow_period': 'Slow moving average period',
                'ma_type': 'Moving average type (sma or ema)',
                'confirm_periods': 'Periods to confirm crossover'
            },
            risk_level="medium",
            recommended_timeframes=['4h', '1d']
        )
        
        # MACD Template
        self.templates['macd'] = StrategyTemplate(
            name="MACD Strategy",
            strategy_type=StrategyType.INDICATOR,
            description="Trades based on MACD crossovers and histogram",
            default_parameters={
                'strategy_class': 'macd',
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9,
                'histogram_threshold': 0.1
            },
            required_parameters=['histogram_threshold'],
            parameter_descriptions={
                'fast_period': 'MACD fast EMA period',
                'slow_period': 'MACD slow EMA period',
                'signal_period': 'MACD signal line period',
                'histogram_threshold': 'Minimum histogram value for signal'
            },
            risk_level="medium",
            recommended_timeframes=['1h', '4h', '1d']
        )
        
        # Combo Indicator Template
        self.templates['combo_indicator'] = StrategyTemplate(
            name="Multi-Indicator Combo",
            strategy_type=StrategyType.INDICATOR,
            description="Combines multiple indicators for confirmation",
            default_parameters={
                'strategy_class': 'combo_indicator',
                'entry_indicators': ['rsi', 'ma_cross'],
                'confirmation_indicators': ['macd'],
                'rsi_oversold': 35,
                'rsi_overbought': 65,
                'require_all_signals': True
            },
            required_parameters=['entry_indicators'],
            parameter_descriptions={
                'entry_indicators': 'List of indicators for entry signals',
                'confirmation_indicators': 'List of indicators for confirmation',
                'rsi_oversold': 'RSI oversold threshold',
                'rsi_overbought': 'RSI overbought threshold',
                'require_all_signals': 'Require all indicators to agree'
            },
            risk_level="low",
            recommended_timeframes=['4h', '1d']
        )
    
    def get_template(self, template_name: str) -> Optional[StrategyTemplate]:
        """
        Get strategy template by name
        
        Args:
            template_name: Template name
            
        Returns:
            Strategy template or None
        """
        return self.templates.get(template_name)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available strategy templates
        
        Returns:
            List of template information
        """
        templates = []
        for name, template in self.templates.items():
            templates.append({
                'name': name,
                'display_name': template.name,
                'type': template.strategy_type.value,
                'description': template.description,
                'risk_level': template.risk_level,
                'recommended_timeframes': template.recommended_timeframes,
                'parameters': template.default_parameters
            })
        return templates
    
    def create_config_from_template(self, template_name: str, config_name: str, 
                                   symbol: str, timeframe: str = "1h",
                                   custom_parameters: Optional[Dict[str, Any]] = None) -> StrategyConfig:
        """
        Create strategy configuration from template
        
        Args:
            template_name: Template to use
            config_name: Name for the new configuration
            symbol: Trading symbol
            timeframe: Trading timeframe
            custom_parameters: Custom parameter overrides
            
        Returns:
            Strategy configuration
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Start with template defaults
        parameters = template.default_parameters.copy()
        
        # Apply custom parameters
        if custom_parameters:
            parameters.update(custom_parameters)
        
        # Validate required parameters
        for required_param in template.required_parameters:
            if required_param not in parameters:
                raise ConfigValidationError(f"Required parameter '{required_param}' not provided")
        
        # Create configuration
        config = StrategyConfig(
            name=config_name,
            strategy_type=template.strategy_type,
            timeframe=timeframe,
            symbols=[symbol],
            parameters=parameters
        )
        
        # Validate configuration
        self._validate_config(config, template)
        
        return config
    
    def save_config(self, config: StrategyConfig, overwrite: bool = False) -> bool:
        """
        Save strategy configuration to disk
        
        Args:
            config: Strategy configuration to save
            overwrite: Whether to overwrite existing config
            
        Returns:
            True if saved successfully
        """
        config_file = self.config_dir / f"{config.name}.yaml"
        
        if config_file.exists() and not overwrite:
            raise ValueError(f"Configuration '{config.name}' already exists")
        
        try:
            # Convert to dictionary
            config_dict = asdict(config)
            config_dict['strategy_type'] = config.strategy_type.value
            
            # Save to YAML file
            with open(config_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            # Cache in memory
            self.saved_configs[config.name] = config
            
            logger.info(f"Strategy configuration '{config.name}' saved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration '{config.name}': {e}")
            return False
    
    def load_config(self, config_name: str) -> Optional[StrategyConfig]:
        """
        Load strategy configuration from disk
        
        Args:
            config_name: Configuration name
            
        Returns:
            Strategy configuration or None
        """
        # Check cache first
        if config_name in self.saved_configs:
            return self.saved_configs[config_name]
        
        config_file = self.config_dir / f"{config_name}.yaml"
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r') as f:
                config_dict = yaml.safe_load(f)
            
            # Convert strategy type back to enum
            config_dict['strategy_type'] = StrategyType(config_dict['strategy_type'])
            
            # Create configuration object
            config = StrategyConfig(**config_dict)
            
            # Cache in memory
            self.saved_configs[config_name] = config
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration '{config_name}': {e}")
            return None
    
    def _load_saved_configs(self):
        """Load all saved configurations from disk"""
        if not self.config_dir.exists():
            return
        
        for config_file in self.config_dir.glob("*.yaml"):
            config_name = config_file.stem
            config = self.load_config(config_name)
            if config:
                self.saved_configs[config_name] = config
        
        logger.info(f"Loaded {len(self.saved_configs)} saved configurations")
    
    def list_saved_configs(self) -> List[Dict[str, Any]]:
        """
        List all saved configurations
        
        Returns:
            List of saved configuration information
        """
        configs = []
        for name, config in self.saved_configs.items():
            configs.append({
                'name': name,
                'type': config.strategy_type.value,
                'timeframe': config.timeframe,
                'symbols': config.symbols,
                'active': config.active,
                'parameters': config.parameters
            })
        return configs
    
    def delete_config(self, config_name: str) -> bool:
        """
        Delete saved configuration
        
        Args:
            config_name: Configuration name
            
        Returns:
            True if deleted successfully
        """
        config_file = self.config_dir / f"{config_name}.yaml"
        
        try:
            if config_file.exists():
                config_file.unlink()
            
            if config_name in self.saved_configs:
                del self.saved_configs[config_name]
            
            logger.info(f"Configuration '{config_name}' deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete configuration '{config_name}': {e}")
            return False
    
    def _validate_config(self, config: StrategyConfig, template: StrategyTemplate):
        """
        Validate strategy configuration against template
        
        Args:
            config: Strategy configuration to validate
            template: Strategy template for validation
        """
        # Check required parameters
        for required_param in template.required_parameters:
            if required_param not in config.parameters:
                raise ConfigValidationError(f"Required parameter '{required_param}' missing")
        
        # Validate parameter types and ranges
        self._validate_parameters(config.parameters, template)
        
        # Validate timeframe
        if (template.recommended_timeframes and 
            config.timeframe not in template.recommended_timeframes):
            logger.warning(f"Timeframe '{config.timeframe}' not recommended for template '{template.name}'")
    
    def _validate_parameters(self, parameters: Dict[str, Any], template: StrategyTemplate):
        """
        Validate parameter values
        
        Args:
            parameters: Parameters to validate
            template: Strategy template
        """
        # Basic validation rules
        validation_rules = {
            'buy_threshold_pct': (0.1, 50.0),
            'sell_threshold_pct': (0.1, 100.0),
            'grid_levels': (3, 50),
            'grid_spacing_pct': (0.1, 10.0),
            'rsi_period': (5, 50),
            'oversold_threshold': (10, 40),
            'overbought_threshold': (60, 90),
            'fast_period': (1, 50),
            'slow_period': (2, 100),
            'base_amount_usd': (1.0, 10000.0),
            'buy_amount': (1.0, 1000.0)
        }
        
        for param, value in parameters.items():
            if param in validation_rules:
                min_val, max_val = validation_rules[param]
                if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                    raise ConfigValidationError(
                        f"Parameter '{param}' must be between {min_val} and {max_val}, got {value}"
                    )
        
        # Specific validation
        if 'fast_period' in parameters and 'slow_period' in parameters:
            if parameters['fast_period'] >= parameters['slow_period']:
                raise ConfigValidationError("Fast period must be less than slow period")
        
        if 'oversold_threshold' in parameters and 'overbought_threshold' in parameters:
            if parameters['oversold_threshold'] >= parameters['overbought_threshold']:
                raise ConfigValidationError("Oversold threshold must be less than overbought threshold")
    
    def export_config_to_json(self, config_name: str) -> Optional[str]:
        """
        Export configuration to JSON string
        
        Args:
            config_name: Configuration name
            
        Returns:
            JSON string or None
        """
        config = self.saved_configs.get(config_name)
        if not config:
            return None
        
        try:
            config_dict = asdict(config)
            config_dict['strategy_type'] = config.strategy_type.value
            return json.dumps(config_dict, indent=2)
        except Exception as e:
            logger.error(f"Failed to export configuration '{config_name}': {e}")
            return None
    
    def import_config_from_json(self, json_str: str, config_name: str) -> bool:
        """
        Import configuration from JSON string
        
        Args:
            json_str: JSON configuration string
            config_name: Name for imported configuration
            
        Returns:
            True if imported successfully
        """
        try:
            config_dict = json.loads(json_str)
            config_dict['name'] = config_name  # Override name
            config_dict['strategy_type'] = StrategyType(config_dict['strategy_type'])
            
            config = StrategyConfig(**config_dict)
            return self.save_config(config, overwrite=True)
            
        except Exception as e:
            logger.error(f"Failed to import configuration '{config_name}': {e}")
            return False