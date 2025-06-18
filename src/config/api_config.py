# src/config/api_config.py

"""
API Client Configuration Management

This module handles configuration for external API clients including
ccxt-gateway and quickchart services.
"""

from typing import Dict, Any, Optional
import os
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class APIClientConfig:
    """Configuration for API clients"""
    # Base URLs
    ccxt_gateway_url: str = "http://ccxt-bridge:3000"
    quickchart_url: str = "http://quickchart:8080"
    
    # Timeout settings
    timeout: int = 30
    max_retries: int = 3
    
    # Rate limiting
    rate_limit_requests: int = 60
    rate_limit_window: int = 60
    
    # Caching
    cache_enabled: bool = True
    default_cache_ttl: int = 60
    market_data_cache_ttl: int = 60
    ticker_cache_ttl: int = 10
    balance_cache_ttl: int = 30
    
    # Chart settings
    default_chart_width: int = 800
    default_chart_height: int = 400
    default_color_scheme: str = "default"
    supported_chart_formats: list = None
    
    def __post_init__(self):
        if self.supported_chart_formats is None:
            self.supported_chart_formats = ['png', 'jpg', 'svg', 'pdf']

@dataclass
class ExchangeConfig:
    """Configuration for exchange connections"""
    name: str
    display_name: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    testnet: bool = False
    enabled: bool = True
    
    # Rate limiting per exchange
    rate_limit: int = 60
    rate_window: int = 60
    
    # Fees
    maker_fee: float = 0.001
    taker_fee: float = 0.001

class APIConfigManager:
    """Manages API client configurations"""
    
    def __init__(self):
        self._config = None
        self._exchanges = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from environment variables and defaults"""
        self._config = APIClientConfig(
            ccxt_gateway_url=os.getenv('CCXT_GATEWAY_URL', 'http://ccxt-bridge:3000'),
            quickchart_url=os.getenv('QUICKCHART_URL', 'http://quickchart:8080'),
            timeout=int(os.getenv('API_TIMEOUT', '30')),
            max_retries=int(os.getenv('API_MAX_RETRIES', '3')),
            rate_limit_requests=int(os.getenv('API_RATE_LIMIT_REQUESTS', '60')),
            rate_limit_window=int(os.getenv('API_RATE_LIMIT_WINDOW', '60')),
            cache_enabled=os.getenv('API_CACHE_ENABLED', 'true').lower() == 'true',
            default_cache_ttl=int(os.getenv('API_DEFAULT_CACHE_TTL', '60')),
            market_data_cache_ttl=int(os.getenv('API_MARKET_DATA_CACHE_TTL', '60')),
            ticker_cache_ttl=int(os.getenv('API_TICKER_CACHE_TTL', '10')),
            balance_cache_ttl=int(os.getenv('API_BALANCE_CACHE_TTL', '30')),
            default_chart_width=int(os.getenv('CHART_DEFAULT_WIDTH', '800')),
            default_chart_height=int(os.getenv('CHART_DEFAULT_HEIGHT', '400')),
            default_color_scheme=os.getenv('CHART_DEFAULT_COLOR_SCHEME', 'default')
        )
        
        logger.info("API configuration loaded")
    
    def get_config(self) -> APIClientConfig:
        """Get API client configuration"""
        return self._config
    
    def add_exchange(self, config: ExchangeConfig) -> None:
        """Add exchange configuration"""
        self._exchanges[config.name] = config
        logger.info(f"Added exchange configuration: {config.name}")
    
    def get_exchange(self, name: str) -> Optional[ExchangeConfig]:
        """Get exchange configuration by name"""
        return self._exchanges.get(name)
    
    def get_all_exchanges(self) -> Dict[str, ExchangeConfig]:
        """Get all exchange configurations"""
        return self._exchanges.copy()
    
    def remove_exchange(self, name: str) -> bool:
        """Remove exchange configuration"""
        if name in self._exchanges:
            del self._exchanges[name]
            logger.info(f"Removed exchange configuration: {name}")
            return True
        return False
    
    def get_enabled_exchanges(self) -> Dict[str, ExchangeConfig]:
        """Get only enabled exchange configurations"""
        return {name: config for name, config in self._exchanges.items() if config.enabled}
    
    def update_config(self, **kwargs) -> None:
        """Update configuration parameters"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                logger.info(f"Updated API config: {key} = {value}")
            else:
                logger.warning(f"Unknown config parameter: {key}")
    
    def validate_config(self) -> bool:
        """Validate configuration parameters"""
        config = self._config
        
        # Validate URLs
        if not config.ccxt_gateway_url or not config.ccxt_gateway_url.startswith('http'):
            logger.error("Invalid ccxt_gateway_url")
            return False
        
        if not config.quickchart_url or not config.quickchart_url.startswith('http'):
            logger.error("Invalid quickchart_url")
            return False
        
        # Validate numeric parameters
        if config.timeout <= 0:
            logger.error("Timeout must be positive")
            return False
        
        if config.max_retries < 0:
            logger.error("Max retries cannot be negative")
            return False
        
        if config.rate_limit_requests <= 0 or config.rate_limit_window <= 0:
            logger.error("Rate limit parameters must be positive")
            return False
        
        # Validate cache TTL values
        if any(ttl < 0 for ttl in [
            config.default_cache_ttl,
            config.market_data_cache_ttl,
            config.ticker_cache_ttl,
            config.balance_cache_ttl
        ]):
            logger.error("Cache TTL values cannot be negative")
            return False
        
        # Validate chart parameters
        if config.default_chart_width <= 0 or config.default_chart_height <= 0:
            logger.error("Chart dimensions must be positive")
            return False
        
        if config.default_color_scheme not in ['default', 'dark']:
            logger.warning(f"Unknown color scheme: {config.default_color_scheme}")
        
        logger.info("API configuration validation passed")
        return True
    
    def get_cache_ttl(self, cache_type: str) -> int:
        """Get cache TTL for specific data type"""
        cache_ttls = {
            'market_data': self._config.market_data_cache_ttl,
            'ticker': self._config.ticker_cache_ttl,
            'balance': self._config.balance_cache_ttl,
            'default': self._config.default_cache_ttl
        }
        return cache_ttls.get(cache_type, self._config.default_cache_ttl)
    
    def get_chart_config(self) -> Dict[str, Any]:
        """Get chart configuration"""
        return {
            'width': self._config.default_chart_width,
            'height': self._config.default_chart_height,
            'color_scheme': self._config.default_color_scheme,
            'supported_formats': self._config.supported_chart_formats
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        config_dict = {
            'api': {
                'ccxt_gateway_url': self._config.ccxt_gateway_url,
                'quickchart_url': self._config.quickchart_url,
                'timeout': self._config.timeout,
                'max_retries': self._config.max_retries,
                'rate_limit_requests': self._config.rate_limit_requests,
                'rate_limit_window': self._config.rate_limit_window,
                'cache_enabled': self._config.cache_enabled,
                'default_cache_ttl': self._config.default_cache_ttl,
                'market_data_cache_ttl': self._config.market_data_cache_ttl,
                'ticker_cache_ttl': self._config.ticker_cache_ttl,
                'balance_cache_ttl': self._config.balance_cache_ttl
            },
            'chart': {
                'default_width': self._config.default_chart_width,
                'default_height': self._config.default_chart_height,
                'default_color_scheme': self._config.default_color_scheme,
                'supported_formats': self._config.supported_chart_formats
            },
            'exchanges': {
                name: {
                    'display_name': config.display_name,
                    'testnet': config.testnet,
                    'enabled': config.enabled,
                    'rate_limit': config.rate_limit,
                    'maker_fee': config.maker_fee,
                    'taker_fee': config.taker_fee
                } for name, config in self._exchanges.items()
            }
        }
        return config_dict

# Global configuration manager
_config_manager: Optional[APIConfigManager] = None

def get_api_config_manager() -> APIConfigManager:
    """Get global API configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = APIConfigManager()
    return _config_manager

def get_api_config() -> APIClientConfig:
    """Get API client configuration"""
    return get_api_config_manager().get_config()

def load_exchange_configs_from_env() -> None:
    """Load exchange configurations from environment variables"""
    config_manager = get_api_config_manager()
    
    # Load KuCoin configuration
    kucoin_api_key = os.getenv('KUCOIN_API_KEY')
    if kucoin_api_key:
        kucoin_config = ExchangeConfig(
            name='kucoin',
            display_name='KuCoin',
            api_key=kucoin_api_key,
            api_secret=os.getenv('KUCOIN_API_SECRET', ''),
            passphrase=os.getenv('KUCOIN_PASSPHRASE', ''),
            testnet=os.getenv('KUCOIN_TESTNET', 'false').lower() == 'true',
            rate_limit=int(os.getenv('KUCOIN_RATE_LIMIT', '60')),
            maker_fee=float(os.getenv('KUCOIN_MAKER_FEE', '0.001')),
            taker_fee=float(os.getenv('KUCOIN_TAKER_FEE', '0.001'))
        )
        config_manager.add_exchange(kucoin_config)
    
    # Load Binance configuration
    binance_api_key = os.getenv('BINANCE_API_KEY')
    if binance_api_key:
        binance_config = ExchangeConfig(
            name='binance',
            display_name='Binance',
            api_key=binance_api_key,
            api_secret=os.getenv('BINANCE_API_SECRET', ''),
            testnet=os.getenv('BINANCE_TESTNET', 'false').lower() == 'true',
            rate_limit=int(os.getenv('BINANCE_RATE_LIMIT', '1200')),  # Binance has higher limits
            maker_fee=float(os.getenv('BINANCE_MAKER_FEE', '0.001')),
            taker_fee=float(os.getenv('BINANCE_TAKER_FEE', '0.001'))
        )
        config_manager.add_exchange(binance_config)
    
    # Add more exchanges as needed
    logger.info("Exchange configurations loaded from environment")

# Example configuration presets
PRESET_CONFIGS = {
    'development': {
        'ccxt_gateway_url': 'http://localhost:3000',
        'quickchart_url': 'http://localhost:8080',
        'timeout': 10,
        'max_retries': 1,
        'cache_enabled': False
    },
    'production': {
        'ccxt_gateway_url': 'http://ccxt-bridge:3000',
        'quickchart_url': 'http://quickchart:8080',
        'timeout': 30,
        'max_retries': 3,
        'cache_enabled': True,
        'rate_limit_requests': 30,  # More conservative in production
        'rate_limit_window': 60
    },
    'testing': {
        'ccxt_gateway_url': 'http://test-ccxt:3000',
        'quickchart_url': 'http://test-chart:8080',
        'timeout': 5,
        'max_retries': 0,
        'cache_enabled': False
    }
}

def apply_preset_config(preset_name: str) -> bool:
    """Apply a preset configuration"""
    if preset_name not in PRESET_CONFIGS:
        logger.error(f"Unknown preset: {preset_name}")
        return False
    
    config_manager = get_api_config_manager()
    preset = PRESET_CONFIGS[preset_name]
    config_manager.update_config(**preset)
    
    logger.info(f"Applied preset configuration: {preset_name}")
    return True