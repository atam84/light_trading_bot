"""
# src/utils/config/settings.py
Settings and configuration management for the trading bot.
"""
import os
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
    
    # Trading defaults
    DEFAULT_MODE: str = os.getenv('DEFAULT_MODE', 'paper')
    DEFAULT_EXCHANGE: str = os.getenv('DEFAULT_EXCHANGE', 'kucoin')
    
    @classmethod
    def load(cls) -> 'Settings':
        """Load settings from environment variables."""
        return cls()
    
    def validate(self) -> bool:
        """Validate required settings."""
        required_vars = ['MONGODB_URL', 'CCXT_GATEWAY_URL']
        for var in required_vars:
            if not getattr(self, var):
                print(f"ERROR: Missing required setting: {var}")
                return False
        return True

# Global settings instance
settings = Settings.load()
