# src/database/models/__init__.py

"""
Database Models Package

This package contains all database models and repositories for the trading bot application.
All models use MongoDB with Motor (async MongoDB driver) and Pydantic for data validation.

Model Categories:
- User Management: Users, sessions, authentication
- Exchange Configuration: API keys, exchange settings
- Strategy Management: Trading strategies and configurations
- Trade Management: Orders, positions, executions
- Backtesting: Backtest results and performance metrics
- Caching: Chart data, API responses, balance cache
- System: Configuration, logging, notifications
- Community: Strategy marketplace, ratings, reviews
"""

# Import all models
from .user import User, UserSession, UserRepository, UserSessionRepository
from .exchange import (
    ExchangeConfig, ExchangeBalance, 
    ExchangeRepository, ExchangeBalanceRepository
)
from .strategy import (
    StrategyConfig, StrategyTemplate, RiskManagement, IndicatorConfig,
    StrategyRepository, StrategyTemplateRepository
)
from .trade import (
    Trade, Position, TradeRepository, PositionRepository
)
from .backtest import (
    Backtest, BacktestTradeLog, BacktestPerformanceMetrics,
    BacktestRepository
)
from .cache import (
    ChartDataCache, TickerCache, BalanceCache, IndicatorCache, APIResponseCache,
    ChartCacheRepository, TickerCacheRepository, BalanceCacheRepository, 
    APIResponseCacheRepository
)
from .system import (
    SystemConfiguration, SystemLog, Notification, TelegramConfig,
    SystemConfigRepository, SystemLogRepository, NotificationRepository,
    TelegramConfigRepository
)
from .community import (
    StrategyMarketplace, StrategyRating, UserFollow, StrategyFavorite, StrategyDownload,
    StrategyMarketplaceRepository, StrategyRatingRepository
)

# Import base classes
from .base import BaseDBModel, BaseRepository, PyObjectId

# Import database connection
from ..connection import db_manager, get_database, init_database, close_database

# Repository instances for easy access
class DatabaseRepositories:
    """Centralized access to all repositories"""
    
    def __init__(self):
        # User management
        self.user = UserRepository()
        self.user_session = UserSessionRepository()
        
        # Exchange management
        self.exchange = ExchangeRepository()
        self.exchange_balance = ExchangeBalanceRepository()
        
        # Strategy management
        self.strategy = StrategyRepository()
        self.strategy_template = StrategyTemplateRepository()
        
        # Trade management
        self.trade = TradeRepository()
        self.position = PositionRepository()
        
        # Backtesting
        self.backtest = BacktestRepository()
        
        # Caching
        self.chart_cache = ChartCacheRepository()
        self.ticker_cache = TickerCacheRepository()
        self.balance_cache = BalanceCacheRepository()
        self.api_cache = APIResponseCacheRepository()
        
        # System
        self.config = SystemConfigRepository()
        self.log = SystemLogRepository()
        self.notification = NotificationRepository()
        self.telegram_config = TelegramConfigRepository()
        
        # Community
        self.marketplace = StrategyMarketplaceRepository()
        self.rating = StrategyRatingRepository()

# Global repository access
repositories = DatabaseRepositories()

# Convenience aliases
user_repo = repositories.user
exchange_repo = repositories.exchange
strategy_repo = repositories.strategy
trade_repo = repositories.trade
backtest_repo = repositories.backtest
config_repo = repositories.config
log_repo = repositories.log

__all__ = [
    # Models
    'User', 'UserSession',
    'ExchangeConfig', 'ExchangeBalance',
    'StrategyConfig', 'StrategyTemplate', 'RiskManagement', 'IndicatorConfig',
    'Trade', 'Position',
    'Backtest', 'BacktestTradeLog', 'BacktestPerformanceMetrics',
    'ChartDataCache', 'TickerCache', 'BalanceCache', 'IndicatorCache', 'APIResponseCache',
    'SystemConfiguration', 'SystemLog', 'Notification', 'TelegramConfig',
    'StrategyMarketplace', 'StrategyRating', 'UserFollow', 'StrategyFavorite', 'StrategyDownload',
    
    # Base classes
    'BaseDBModel', 'BaseRepository', 'PyObjectId',
    
    # Database connection
    'db_manager', 'get_database', 'init_database', 'close_database',
    
    # Repository access
    'repositories', 'DatabaseRepositories',
    
    # Convenience aliases
    'user_repo', 'exchange_repo', 'strategy_repo', 'trade_repo', 'backtest_repo',
    'config_repo', 'log_repo'
]