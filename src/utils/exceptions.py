# src/utils/exceptions.py

"""
Custom exceptions for the trading bot application
"""

class TradingBotException(Exception):
    """Base exception for all trading bot errors"""
    pass

class ConfigurationError(TradingBotException):
    """Configuration related errors"""
    pass

class DatabaseError(TradingBotException):
    """Database operation errors"""
    pass

class APIError(TradingBotException):
    """General API error"""
    
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code

class AuthenticationError(APIError):
    """Authentication failed error"""
    pass

class RateLimitError(APIError):
    """Rate limit exceeded error"""
    pass

class TradingError(TradingBotException):
    """Trading operation errors"""
    pass

class ChartError(TradingBotException):
    """Chart generation errors"""
    pass

class StrategyError(TradingBotException):
    """Strategy execution errors"""
    pass

class RiskManagementError(TradingBotException):
    """Risk management validation errors"""
    pass

class OrderError(TradingError):
    """Order placement/management errors"""
    pass

class BalanceError(TradingError):
    """Insufficient balance errors"""
    pass

class MarketDataError(APIError):
    """Market data retrieval errors"""
    pass

class ValidationError(TradingBotException):
    """Data validation errors"""
    pass

class NotificationError(TradingBotException):
    """Notification delivery errors"""
    pass