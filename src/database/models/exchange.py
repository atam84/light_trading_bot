# src/database/models/exchange.py

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import Field, validator
from enum import Enum
from src.database.models.base import (
    BaseDBModel, BaseRepository, TimestampMixin, 
    UserOwnershipMixin, ActiveMixin, EncryptionMixin, PyObjectId
)

class ExchangeType(str, Enum):
    """Supported exchange types"""
    KUCOIN = "kucoin"
    BINANCE = "binance"
    OKX = "okx"
    BYBIT = "bybit"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    BITFINEX = "bitfinex"
    HUOBI = "huobi"

class ExchangeEnvironment(str, Enum):
    """Exchange environment types"""
    PRODUCTION = "production"
    SANDBOX = "sandbox"
    TESTNET = "testnet"

class ExchangeConfig(BaseDBModel, TimestampMixin, UserOwnershipMixin, ActiveMixin, EncryptionMixin):
    """Exchange configuration model with encrypted API keys"""
    
    exchange_name: ExchangeType = Field(..., description="Exchange identifier")
    display_name: str = Field(..., min_length=1, max_length=100, description="User-friendly name")
    environment: ExchangeEnvironment = Field(default=ExchangeEnvironment.PRODUCTION)
    
    # Encrypted API credentials
    api_key_encrypted: str = Field(..., description="Encrypted API key")
    api_secret_encrypted: str = Field(..., description="Encrypted API secret")
    passphrase_encrypted: Optional[str] = Field(None, description="Encrypted passphrase (for some exchanges)")
    
    # Exchange settings
    default_quote_currency: str = Field(default="USDT", description="Default quote currency")
    fee_rate: float = Field(default=0.001, ge=0, le=1, description="Trading fee rate")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, description="Requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Trading preferences
    enable_futures: bool = Field(default=False, description="Enable futures trading")
    enable_margin: bool = Field(default=False, description="Enable margin trading")
    enable_options: bool = Field(default=False, description="Enable options trading")
    
    # Connection settings
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retries: int = Field(default=3, description="Number of retries for failed requests")
    
    # Status tracking
    last_connection_test: Optional[datetime] = None
    connection_status: str = Field(default="unknown", description="Last known connection status")
    last_error: Optional[str] = None
    
    # Statistics
    total_requests: int = Field(default=0)
    successful_requests: int = Field(default=0)
    failed_requests: int = Field(default=0)
    last_used: Optional[datetime] = None
    
    @property
    def collection_name(self) -> str:
        return "exchanges"
    
    @validator('display_name')
    def validate_display_name(cls, v):
        return v.strip()
    
    @validator('fee_rate')
    def validate_fee_rate(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Fee rate must be between 0 and 1 (0-100%)')
        return v
    
    @classmethod
    def create_with_credentials(cls, user_id: str, exchange_name: str, display_name: str,
                              api_key: str, api_secret: str, passphrase: str = None, **kwargs) -> 'ExchangeConfig':
        """Create exchange config with encrypted credentials"""
        
        # Encrypt credentials
        api_key_encrypted = cls.encrypt_value(api_key)
        api_secret_encrypted = cls.encrypt_value(api_secret)
        passphrase_encrypted = cls.encrypt_value(passphrase) if passphrase else None
        
        return cls(
            user_id=PyObjectId(user_id),
            exchange_name=exchange_name,
            display_name=display_name,
            api_key_encrypted=api_key_encrypted,
            api_secret_encrypted=api_secret_encrypted,
            passphrase_encrypted=passphrase_encrypted,
            **kwargs
        )
    
    def get_decrypted_credentials(self) -> Dict[str, str]:
        """Get decrypted API credentials"""
        credentials = {
            'api_key': self.decrypt_value(self.api_key_encrypted),
            'api_secret': self.decrypt_value(self.api_secret_encrypted)
        }
        
        if self.passphrase_encrypted:
            credentials['passphrase'] = self.decrypt_value(self.passphrase_encrypted)
        
        return credentials
    
    def update_credentials(self, api_key: str = None, api_secret: str = None, passphrase: str = None):
        """Update encrypted credentials"""
        if api_key:
            self.api_key_encrypted = self.encrypt_value(api_key)
        if api_secret:
            self.api_secret_encrypted = self.encrypt_value(api_secret)
        if passphrase:
            self.passphrase_encrypted = self.encrypt_value(passphrase)
        elif passphrase is None:
            self.passphrase_encrypted = None
    
    def update_connection_status(self, status: str, error: str = None):
        """Update connection status"""
        self.connection_status = status
        self.last_connection_test = datetime.now(timezone.utc)
        self.last_error = error
        if status == "success":
            self.last_used = self.last_connection_test
    
    def record_request(self, success: bool = True):
        """Record API request statistics"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.last_used = datetime.now(timezone.utc)
    
    def get_success_rate(self) -> float:
        """Calculate request success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Return safe dictionary without sensitive data"""
        data = self.dict()
        # Remove encrypted credentials
        data.pop('api_key_encrypted', None)
        data.pop('api_secret_encrypted', None)
        data.pop('passphrase_encrypted', None)
        return data

class ExchangeBalance(BaseDBModel, TimestampMixin):
    """Exchange balance snapshot"""
    
    exchange_config_id: PyObjectId = Field(..., description="Exchange configuration ID")
    user_id: PyObjectId = Field(..., description="User ID")
    
    # Balance data
    balances: Dict[str, Dict[str, float]] = Field(default={}, description="Asset balances")
    total_balance_usd: float = Field(default=0.0, description="Total balance in USD")
    
    # Metadata
    snapshot_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_source: str = Field(default="api", description="Source of balance data")
    
    @property
    def collection_name(self) -> str:
        return "exchange_balances"
    
    def get_asset_balance(self, asset: str) -> Dict[str, float]:
        """Get balance for specific asset"""
        return self.balances.get(asset, {'free': 0.0, 'used': 0.0, 'total': 0.0})
    
    def get_free_balance(self, asset: str) -> float:
        """Get free balance for asset"""
        return self.get_asset_balance(asset).get('free', 0.0)
    
    def get_total_balance(self, asset: str) -> float:
        """Get total balance for asset"""
        return self.get_asset_balance(asset).get('total', 0.0)
    
    def has_sufficient_balance(self, asset: str, amount: float) -> bool:
        """Check if there's sufficient free balance"""
        return self.get_free_balance(asset) >= amount

class ExchangeRepository(BaseRepository[ExchangeConfig]):
    """Repository for ExchangeConfig operations"""
    
    def __init__(self):
        super().__init__(ExchangeConfig)
    
    async def get_user_exchanges(self, user_id: str, active_only: bool = True) -> List[ExchangeConfig]:
        """Get all exchanges for a user"""
        filter_dict = {"user_id": PyObjectId(user_id)}
        if active_only:
            filter_dict["active"] = True
        
        return await self.get_many(
            filter_dict=filter_dict,
            sort=[("created_at", -1)]
        )
    
    async def get_by_name_and_user(self, user_id: str, exchange_name: str) -> Optional[ExchangeConfig]:
        """Get exchange config by name and user"""
        return await self.get_one({
            "user_id": PyObjectId(user_id),
            "exchange_name": exchange_name
        })
    
    async def create_exchange(self, user_id: str, exchange_name: str, display_name: str,
                            api_key: str, api_secret: str, passphrase: str = None, **kwargs) -> ExchangeConfig:
        """Create new exchange configuration"""
        
        # Check if exchange already exists for user
        existing = await self.get_by_name_and_user(user_id, exchange_name)
        if existing:
            raise ValueError(f"Exchange {exchange_name} already configured for user")
        
        exchange_config = ExchangeConfig.create_with_credentials(
            user_id=user_id,
            exchange_name=exchange_name,
            display_name=display_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            **kwargs
        )
        
        return await self.create(exchange_config)
    
    async def update_credentials(self, exchange_id: str, api_key: str = None, 
                               api_secret: str = None, passphrase: str = None) -> Optional[ExchangeConfig]:
        """Update exchange credentials"""
        exchange = await self.get_by_id(exchange_id)
        if not exchange:
            return None
        
        update_data = {}
        if api_key:
            update_data['api_key_encrypted'] = ExchangeConfig.encrypt_value(api_key)
        if api_secret:
            update_data['api_secret_encrypted'] = ExchangeConfig.encrypt_value(api_secret)
        if passphrase:
            update_data['passphrase_encrypted'] = ExchangeConfig.encrypt_value(passphrase)
        elif passphrase is None:
            update_data['passphrase_encrypted'] = None
        
        return await self.update(exchange_id, update_data)
    
    async def update_connection_status(self, exchange_id: str, status: str, error: str = None) -> bool:
        """Update exchange connection status"""
        update_data = {
            'connection_status': status,
            'last_connection_test': datetime.now(timezone.utc),
            'last_error': error
        }
        
        if status == "success":
            update_data['last_used'] = datetime.now(timezone.utc)
        
        result = await self.update(exchange_id, update_data)
        return result is not None
    
    async def record_request(self, exchange_id: str, success: bool = True) -> bool:
        """Record API request for statistics"""
        exchange = await self.get_by_id(exchange_id)
        if not exchange:
            return False
        
        update_data = {
            'total_requests': exchange.total_requests + 1,
            'last_used': datetime.now(timezone.utc)
        }
        
        if success:
            update_data['successful_requests'] = exchange.successful_requests + 1
        else:
            update_data['failed_requests'] = exchange.failed_requests + 1
        
        result = await self.update(exchange_id, update_data)
        return result is not None
    
    async def get_exchange_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get exchange usage statistics for user"""
        exchanges = await self.get_user_exchanges(user_id, active_only=False)
        
        total_exchanges = len(exchanges)
        active_exchanges = len([ex for ex in exchanges if ex.active])
        total_requests = sum(ex.total_requests for ex in exchanges)
        successful_requests = sum(ex.successful_requests for ex in exchanges)
        
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        return {
            'total_exchanges': total_exchanges,
            'active_exchanges': active_exchanges,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate': success_rate,
            'exchanges': [ex.to_safe_dict() for ex in exchanges]
        }

class ExchangeBalanceRepository(BaseRepository[ExchangeBalance]):
    """Repository for ExchangeBalance operations"""
    
    def __init__(self):
        super().__init__(ExchangeBalance)
    
    async def save_balance_snapshot(self, exchange_config_id: str, user_id: str, 
                                  balances: Dict[str, Dict[str, float]], 
                                  total_balance_usd: float = 0.0) -> ExchangeBalance:
        """Save balance snapshot"""
        balance_data = {
            'exchange_config_id': PyObjectId(exchange_config_id),
            'user_id': PyObjectId(user_id),
            'balances': balances,
            'total_balance_usd': total_balance_usd,
            'snapshot_time': datetime.now(timezone.utc)
        }
        
        return await self.create(balance_data)
    
    async def get_latest_balance(self, exchange_config_id: str) -> Optional[ExchangeBalance]:
        """Get latest balance for exchange"""
        balances = await self.get_many(
            filter_dict={'exchange_config_id': PyObjectId(exchange_config_id)},
            sort=[('snapshot_time', -1)],
            limit=1
        )
        return balances[0] if balances else None
    
    async def get_user_balances(self, user_id: str) -> List[ExchangeBalance]:
        """Get latest balances for all user exchanges"""
        return await self.get_many(
            filter_dict={'user_id': PyObjectId(user_id)},
            sort=[('snapshot_time', -1)]
        )

# Repository instances
exchange_repository = ExchangeRepository()
exchange_balance_repository = ExchangeBalanceRepository()