"""
# src/utils/config/settings.py
Settings and configuration management for the trading bot.
"""
import os
import yaml
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass
class Settings:
    """Main settings class for the trading bot."""
    
    # Database settings
    MONGODB_URL: str = os.getenv('MONGODB_URL', 'mongodb://mongodb:27017/trading_bot')
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    
    # External services
    CCXT_GATEWAY_URL: str = os.getenv('CCXT_GATEWAY_URL', 'http://ccxt-bridge:3000')
    QUICKCHART_URL: str = os.getenv('QUICKCHART_URL', 'http://quickchart:3400')
    
    # Security
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-here')
    ENCRYPTION_KEY: str = os.getenv('ENCRYPTION_KEY', 'your-encryption-key-here')
    
    # Application
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    DEBUG: bool = os.getenv('DEBUG', 'true').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', 'detailed')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/trading_bot.log')
    
    # Trading defaults
    DEFAULT_TRADING_MODE: str = os.getenv('DEFAULT_TRADING_MODE', 'paper')
    DEFAULT_EXCHANGE: str = os.getenv('DEFAULT_EXCHANGE', 'kucoin')
    
    def __init__(self, config_file: Optional[str] = None, env_file: Optional[str] = None):
        """Initialize settings from config file and environment variables."""
        
        # Load from config file if provided
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    # Apply config values (this is simplified - you can enhance this)
                    for key, value in config_data.items():
                        if hasattr(self, key.upper()):
                            setattr(self, key.upper(), value)
            except Exception as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
        
        # Load environment variables (they override config file)
        for field_name, field in self.__dataclass_fields__.items():
            env_value = os.getenv(field_name)
            if env_value is not None:
                # Convert string env vars to appropriate types
                if field.type == bool:
                    setattr(self, field_name, env_value.lower() in ('true', '1', 'yes'))
                else:
                    setattr(self, field_name, env_value)
    
    def validate(self) -> bool:
        """Validate required settings."""
        required_vars = ['MONGODB_URL', 'CCXT_GATEWAY_URL']
        for var in required_vars:
            if not getattr(self, var):
                print(f"ERROR: Missing required setting: {var}")
                return False
        return True

# For backward compatibility
def load_settings() -> Settings:
    """Load settings instance."""
    return Settings()
