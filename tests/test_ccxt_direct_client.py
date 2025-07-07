import pytest
from unittest.mock import AsyncMock, patch

from src.api_clients.ccxt_direct import CCXTDirectClient
from src.api_clients.ccxt_gateway import OrderInfo, MarketData, BalanceInfo

@pytest.mark.asyncio
async def test_get_market_data_success():
    client = CCXTDirectClient()
    mock_ex = AsyncMock()
    mock_ex.fetch_ohlcv.return_value = [
        [1640995200000, 1, 2, 0.5, 1.5, 10.0]
    ]
    with patch('ccxt.async_support.binance', return_value=mock_ex):
        data = await client.get_market_data('BTC/USDT', '1h', 1, 'binance')
        assert isinstance(data[0], MarketData)
        assert data[0].open == 1
    mock_ex.close.assert_awaited()

@pytest.mark.asyncio
async def test_place_order_success():
    client = CCXTDirectClient()
    order_dict = {
        'id': '1',
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'type': 'market',
        'amount': 0.1,
        'price': None,
        'filled': 0.0,
        'remaining': 0.1,
        'status': 'open',
        'timestamp': 0
    }
    mock_ex = AsyncMock()
    mock_ex.create_order.return_value = order_dict
    with patch('ccxt.async_support.binance', return_value=mock_ex):
        order = await client.place_order('binance', 'k', 's', 'BTC/USDT', 'buy', 'market', 0.1)
        assert isinstance(order, OrderInfo)
    mock_ex.close.assert_awaited()

@pytest.mark.asyncio
async def test_get_balance_success():
    client = CCXTDirectClient()
    balance_data = {
        'total': {'BTC': 1.0},
        'free': {'BTC': 0.5},
        'used': {'BTC': 0.5}
    }
    mock_ex = AsyncMock()
    mock_ex.fetch_balance.return_value = balance_data
    with patch('ccxt.async_support.binance', return_value=mock_ex):
        bal = await client.get_balance('binance', 'k', 's')
        assert 'BTC' in bal
        assert isinstance(bal['BTC'], BalanceInfo)
    mock_ex.close.assert_awaited()
