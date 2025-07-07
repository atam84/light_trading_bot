# tests/test_api_clients.py

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from src.api_clients import (
    CCXTGatewayClient, 
    QuickChartClient, 
    APIClientManager,
    MarketData, 
    TickerData, 
    BalanceInfo, 
    OrderInfo,
    ChartConfig,
    CandlestickPoint,
    TradeMarker
)
from src.api_clients.base_client import APIResponse, BaseHTTPClient
from src.utils.exceptions import APIError, TradingError, ChartError

class TestBaseHTTPClient:
    """Test cases for BaseHTTPClient"""
    
    @pytest.fixture
    def base_client(self):
        return BaseHTTPClient("http://test.com")
    
    def test_build_url(self, base_client):
        """Test URL building with parameters"""
        url = base_client._build_url("/test", {"param1": "value1", "param2": "value2"})
        assert "http://test.com/test" in url
        assert "param1=value1" in url
        assert "param2=value2" in url
    
    def test_build_url_no_params(self, base_client):
        """Test URL building without parameters"""
        url = base_client._build_url("/test")
        assert url == "http://test.com/test"
    
    def test_cache_key_generation(self, base_client):
        """Test cache key generation"""
        headers = {"X-EXCHANGE": "kucoin", "X-API-KEY": "test_key"}
        key = base_client._get_cache_key("GET", "http://test.com", headers)
        assert "GET" in key
        assert "X-EXCHANGE:kucoin" in key
        assert "X-API-KEY:test_key" in key
    
    def test_cache_operations(self, base_client):
        """Test cache store and retrieve operations"""
        response = APIResponse(200, {"test": "data"}, {}, True)
        cache_key = "test_key"
        
        # Test caching
        base_client._cache_response(cache_key, response)
        assert cache_key in base_client._cache
        
        # Test retrieval
        cached = base_client._get_cached_response(cache_key, 60)
        assert cached is not None
        assert cached.data == response.data
        
        # Test cache stats
        stats = base_client.get_cache_stats()
        assert stats['total_entries'] == 1
        
        # Test cache clear
        base_client.clear_cache()
        assert len(base_client._cache) == 0

class TestCCXTGatewayClient:
    """Test cases for CCXTGatewayClient"""
    
    @pytest.fixture
    def ccxt_client(self):
        return CCXTGatewayClient("http://ccxt-bridge:3000")
    
    @pytest.fixture
    def sample_market_data(self):
        return [
            {
                "symbol": "BTC/USDT",
                "interval": "1h",
                "timestamp": 1640995200000,
                "open": 46000,
                "high": 46500,
                "low": 45800,
                "close": 46200,
                "volume": 150.5,
                "datetime": "2022-01-01T00:00:00.000Z"
            }
        ]
    
    @pytest.fixture
    def sample_balance_data(self):
        return {
            "BTC": {"free": 0.5, "used": 0.1, "total": 0.6},
            "USDT": {"free": 1000.0, "used": 500.0, "total": 1500.0}
        }
    
    def test_auth_headers(self, ccxt_client):
        """Test authentication header generation"""
        headers = ccxt_client._get_auth_headers(
            "kucoin", "api_key", "api_secret", "passphrase"
        )
        
        assert headers["X-EXCHANGE"] == "kucoin"
        assert headers["X-API-KEY"] == "api_key"
        assert headers["X-API-SECRET"] == "api_secret"
        assert headers["X-API-PASSPHRASE"] == "passphrase"
    
    def test_symbol_validation(self, ccxt_client):
        """Test symbol format validation"""
        # Valid formats
        assert ccxt_client.validate_symbol_format("BTC/USDT") == "BTC/USDT"
        assert ccxt_client.validate_symbol_format("btc-usdt") == "BTC/USDT"
        assert ccxt_client.validate_symbol_format("eth_usdc") == "ETH/USDC"
        
        # Invalid formats
        with pytest.raises(ValueError):
            ccxt_client.validate_symbol_format("BTCUSDT")  # No separator
        
        with pytest.raises(ValueError):
            ccxt_client.validate_symbol_format("BTC/")  # Empty quote
    
    @pytest.mark.asyncio
    async def test_get_market_data_success(self, ccxt_client, sample_market_data):
        """Test successful market data retrieval"""
        mock_response = APIResponse(200, sample_market_data, {}, True)
        
        with patch.object(ccxt_client, 'get', return_value=mock_response):
            result = await ccxt_client.get_market_data("BTC/USDT", "1h", 150)
            
            assert len(result) == 1
            assert isinstance(result[0], MarketData)
            assert result[0].symbol == "BTC/USDT"
            assert result[0].interval == "1h"
            assert result[0].open == 46000
    
    @pytest.mark.asyncio
    async def test_get_market_data_invalid_interval(self, ccxt_client):
        """Test market data with invalid interval"""
        with pytest.raises(ValueError, match="Unsupported interval"):
            await ccxt_client.get_market_data("BTC/USDT", "3h")
    
    @pytest.mark.asyncio
    async def test_get_balance_success(self, ccxt_client, sample_balance_data):
        """Test successful balance retrieval"""
        mock_response = APIResponse(200, sample_balance_data, {}, True)
        
        with patch.object(ccxt_client, 'get', return_value=mock_response):
            result = await ccxt_client.get_balance("kucoin", "key", "secret")
            
            assert "BTC" in result
            assert "USDT" in result
            assert isinstance(result["BTC"], BalanceInfo)
            assert result["BTC"].free == 0.5
            assert result["USDT"].total == 1500.0
    
    @pytest.mark.asyncio
    async def test_place_order_success(self, ccxt_client):
        """Test successful order placement"""
        order_response = {
            "id": "12345",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "amount": 0.01,
            "price": None,
            "filled": 0,
            "remaining": 0.01,
            "status": "open",
            "timestamp": 1640995200000
        }
        mock_response = APIResponse(200, order_response, {}, True)
        
        with patch.object(ccxt_client, 'post', return_value=mock_response):
            result = await ccxt_client.place_order(
                "kucoin", "key", "secret", "BTC/USDT", "buy", "market", 0.01
            )
            
            assert isinstance(result, OrderInfo)
            assert result.id == "12345"
            assert result.symbol == "BTC/USDT"
            assert result.side == "buy"
    
    @pytest.mark.asyncio
    async def test_place_order_validation(self, ccxt_client):
        """Test order placement validation"""
        # Invalid side
        with pytest.raises(ValueError, match="Invalid side"):
            await ccxt_client.place_order(
                "kucoin", "key", "secret", "BTC/USDT", "invalid", "market", 0.01
            )
        
        # Invalid order type
        with pytest.raises(ValueError, match="Invalid order type"):
            await ccxt_client.place_order(
                "kucoin", "key", "secret", "BTC/USDT", "buy", "invalid", 0.01
            )
        
        # Limit order without price
        with pytest.raises(ValueError, match="Price is required"):
            await ccxt_client.place_order(
                "kucoin", "key", "secret", "BTC/USDT", "buy", "limit", 0.01
            )
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, ccxt_client):
        """Test API error handling"""
        error_response = APIResponse(400, {"error": "Bad request"}, {}, False, "Bad request")
        
        with patch.object(ccxt_client, 'get', return_value=error_response):
            with pytest.raises(TradingError):
                await ccxt_client.get_market_data("BTC/USDT")

class TestQuickChartClient:
    """Test cases for QuickChartClient"""
    
    @pytest.fixture
    def chart_client(self):
        return QuickChartClient("http://quickchart:8080")
    
    @pytest.fixture
    def sample_market_data(self):
        return [
            MarketData("BTC/USDT", "1h", 1640995200000, 46000, 46500, 45800, 46200, 150.5),
            MarketData("BTC/USDT", "1h", 1640998800000, 46200, 46800, 46000, 46500, 200.0)
        ]
    
    @pytest.fixture
    def sample_trade_markers(self):
        return [
            TradeMarker(1640995200000, 46000, "buy", 0.01, 46000),
            TradeMarker(1640998800000, 46500, "sell", 0.01, 46500)
        ]
    
    def test_market_data_conversion(self, chart_client, sample_market_data):
        """Test conversion of market data to candlestick points"""
        candlestick_data = chart_client._convert_market_data_to_candlestick(sample_market_data)
        
        assert len(candlestick_data) == 2
        assert isinstance(candlestick_data[0], CandlestickPoint)
        assert candlestick_data[0].open == 46000
        assert candlestick_data[0].high == 46500
        assert candlestick_data[0].low == 45800
        assert candlestick_data[0].close == 46200
    
    def test_candlestick_chart_config(self, chart_client, sample_market_data):
        """Test candlestick chart configuration creation"""
        candlestick_data = chart_client._convert_market_data_to_candlestick(sample_market_data)
        config = ChartConfig("candlestick", title="Test Chart")
        
        chart_config = chart_client._create_candlestick_chart_config(
            candlestick_data, config, "default", True
        )
        
        assert chart_config["type"] == "candlestick"
        assert len(chart_config["data"]["datasets"]) >= 1  # Price + optionally volume
        assert chart_config["options"]["plugins"]["title"]["text"] == "Test Chart"
    
    def test_trade_markers_addition(self, chart_client, sample_trade_markers):
        """Test adding trade markers to chart configuration"""
        chart_config = {
            "type": "candlestick",
            "data": {"datasets": []},
            "options": {}
        }
        
        updated_config = chart_client._add_trade_markers_to_config(
            chart_config, sample_trade_markers
        )
        
        # Should have buy and sell marker datasets
        datasets = updated_config["data"]["datasets"]
        marker_datasets = [d for d in datasets if d.get("type") == "scatter"]
        assert len(marker_datasets) == 2  # Buy and sell markers
    
    @pytest.mark.asyncio
    async def test_create_candlestick_chart_success(self, chart_client, sample_market_data):
        """Test successful candlestick chart creation"""
        # Mock successful chart response
        chart_bytes = b"fake_chart_data"
        mock_response = APIResponse(200, chart_bytes, {}, True)
        
        with patch.object(chart_client, 'post', return_value=mock_response):
            result = await chart_client.create_candlestick_chart(sample_market_data)
            
            assert isinstance(result, bytes)
            assert result == chart_bytes
    
    @pytest.mark.asyncio
    async def test_create_chart_empty_data(self, chart_client):
        """Test chart creation with empty data"""
        with pytest.raises(ValueError, match="Market data cannot be empty"):
            await chart_client.create_candlestick_chart([])
    
    @pytest.mark.asyncio
    async def test_chart_error_handling(self, chart_client, sample_market_data):
        """Test chart generation error handling"""
        error_response = APIResponse(500, {"error": "Internal error"}, {}, False, "Internal error")
        
        with patch.object(chart_client, 'post', return_value=error_response):
            with pytest.raises(ChartError):
                await chart_client.create_candlestick_chart(sample_market_data)
    
    def test_color_schemes(self, chart_client):
        """Test color scheme functionality"""
        schemes = chart_client.get_available_color_schemes()
        assert "default" in schemes
        assert "dark" in schemes
        
        # Test color scheme access
        default_colors = chart_client.color_schemes["default"]
        assert "candlestick_up" in default_colors
        assert "candlestick_down" in default_colors
    
    def test_supported_formats(self, chart_client):
        """Test supported chart formats"""
        formats = chart_client.get_supported_formats()
        assert "png" in formats
        assert "jpg" in formats
        assert "svg" in formats
        assert "pdf" in formats

class TestAPIClientManager:
    """Test cases for APIClientManager"""
    
    @pytest.fixture
    def api_manager(self):
        return APIClientManager()
    
    @pytest.mark.asyncio
    async def test_initialization(self, api_manager):
        """Test API manager initialization"""
        await api_manager.initialize()
        
        assert api_manager._initialized
        assert api_manager._ccxt_client is not None
        assert api_manager._chart_client is not None
        
        # Test property access
        ccxt_client = api_manager.ccxt
        chart_client = api_manager.charts
        
        assert isinstance(ccxt_client, CCXTGatewayClient)
        assert isinstance(chart_client, QuickChartClient)
        
        await api_manager.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, api_manager):
        """Test API manager as context manager"""
        async with api_manager as manager:
            assert manager._initialized
            assert manager.ccxt is not None
            assert manager.charts is not None
        
        # Should be closed after context
        assert not manager._initialized
    
    @pytest.mark.asyncio
    async def test_health_check(self, api_manager):
        """Test health check functionality"""
        # Mock health check responses
        with patch.object(CCXTGatewayClient, 'health_check', return_value=True), \
             patch.object(QuickChartClient, 'health_check', return_value=True):
            
            health = await api_manager.health_check()
            
            assert "ccxt_gateway" in health
            assert "quickchart" in health
            assert health["ccxt_gateway"] is True
            assert health["quickchart"] is True
    
    def test_uninitialized_access(self, api_manager):
        """Test accessing clients before initialization"""
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = api_manager.ccxt
        
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = api_manager.charts

    @pytest.mark.asyncio
    async def test_direct_client_initialization(self, monkeypatch):
        """Ensure manager can initialize direct ccxt client"""
        conf = {'api.ccxt_gateway_url': 'http://ccxt', 'api.quickchart_url': 'http://chart', 'api.use_gateway': False}
        monkeypatch.setattr('src.api_clients.get_config', lambda: conf)
        manager = APIClientManager()
        await manager.initialize()
        from src.api_clients.ccxt_direct import CCXTDirectClient
        assert isinstance(manager.ccxt, CCXTDirectClient)
        await manager.close()

@pytest.mark.asyncio
async def test_convenience_functions():
    """Test convenience functions"""
    # Mock the API manager and clients
    with patch('src.api_clients.api_clients') as mock_context:
        mock_manager = AsyncMock()
        mock_manager.ccxt = AsyncMock()
        mock_manager.charts = AsyncMock()
        
        # Configure the async context manager
        mock_context.return_value.__aenter__.return_value = mock_manager
        mock_context.return_value.__aexit__.return_value = None
        
        # Mock market data response
        sample_data = [MarketData("BTC/USDT", "1h", 1640995200000, 46000, 46500, 45800, 46200, 150.5)]
        mock_manager.ccxt.get_market_data.return_value = sample_data
        
        # Test get_market_data convenience function
        from src.api_clients import get_market_data
        result = await get_market_data("BTC/USDT")
        
        assert result == sample_data
        mock_manager.ccxt.get_market_data.assert_called_once()

class TestDataContainers:
    """Test data container classes"""
    
    def test_market_data_from_dict(self):
        """Test MarketData creation from dictionary"""
        data = {
            "symbol": "BTC/USDT",
            "interval": "1h", 
            "timestamp": 1640995200000,
            "open": 46000,
            "high": 46500,
            "low": 45800,
            "close": 46200,
            "volume": 150.5,
            "datetime": "2022-01-01T00:00:00.000Z"
        }
        
        market_data = MarketData.from_dict(data)
        
        assert market_data.symbol == "BTC/USDT"
        assert market_data.interval == "1h"
        assert market_data.open == 46000
        assert market_data.volume == 150.5
        assert market_data.datetime_str == "2022-01-01T00:00:00.000Z"
    
    def test_balance_info_from_dict(self):
        """Test BalanceInfo creation from dictionary"""
        data = {"free": 100.0, "used": 50.0, "total": 150.0}
        
        balance = BalanceInfo.from_dict("USDT", data)
        
        assert balance.currency == "USDT"
        assert balance.free == 100.0
        assert balance.used == 50.0
        assert balance.total == 150.0
    
    def test_order_info_from_dict(self):
        """Test OrderInfo creation from dictionary"""
        data = {
            "id": "12345",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "market",
            "amount": 0.01,
            "price": 46000,
            "filled": 0.005,
            "remaining": 0.005,
            "status": "partial",
            "timestamp": 1640995200000,
            "fee": {"cost": 1.0}
        }
        
        order = OrderInfo.from_dict(data)
        
        assert order.id == "12345"
        assert order.symbol == "BTC/USDT"
        assert order.side == "buy"
        assert order.amount == 0.01
        assert order.fee == 1.0

if __name__ == "__main__":
    pytest.main([__file__])
