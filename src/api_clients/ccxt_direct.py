import logging
from typing import List, Dict, Any, Optional

import ccxt.async_support as ccxt

from .ccxt_gateway import MarketData, BalanceInfo, OrderInfo, TickerData, TradeInfo
from ..utils.exceptions import TradingError

logger = logging.getLogger(__name__)


class CCXTDirectClient:
    """Direct ccxt client using the async support module."""

    def __init__(self) -> None:
        # We do not maintain persistent exchange instances for simplicity
        pass

    async def _create_exchange(self, exchange: str, api_key: Optional[str] = None,
                               api_secret: Optional[str] = None,
                               passphrase: Optional[str] = None):
        try:
            exchange_cls = getattr(ccxt, exchange)
        except AttributeError as e:
            raise TradingError(f"Unsupported exchange: {exchange}") from e

        params = {}
        if api_key:
            params['apiKey'] = api_key
        if api_secret:
            params['secret'] = api_secret
        if passphrase:
            params['password'] = passphrase

        return exchange_cls(params)

    async def get_market_data(self, symbol: str, interval: str = '1h', limit: int = 150,
                              exchange: str = 'binance') -> List[MarketData]:
        """Fetch historical market data via ccxt."""
        ex = await self._create_exchange(exchange)
        try:
            raw = await ex.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
            result = [
                MarketData(
                    symbol=symbol,
                    interval=interval,
                    timestamp=item[0],
                    open=item[1],
                    high=item[2],
                    low=item[3],
                    close=item[4],
                    volume=item[5]
                ) for item in raw
            ]
            return result
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            raise TradingError(str(e))
        finally:
            await ex.close()

    async def get_balance(self, exchange: str, api_key: str, api_secret: str,
                          passphrase: Optional[str] = None) -> Dict[str, BalanceInfo]:
        ex = await self._create_exchange(exchange, api_key, api_secret, passphrase)
        try:
            bal = await ex.fetch_balance()
            balances = {}
            total = bal.get('total', {}) or {}
            free = bal.get('free', {}) or {}
            used = bal.get('used', {}) or {}
            for cur in total:
                balances[cur] = BalanceInfo(
                    currency=cur,
                    free=float(free.get(cur, 0)),
                    used=float(used.get(cur, 0)),
                    total=float(total.get(cur, 0))
                )
            return balances
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise TradingError(str(e))
        finally:
            await ex.close()

    async def place_order(self, exchange: str, api_key: str, api_secret: str,
                          symbol: str, side: str, order_type: str, amount: float,
                          price: Optional[float] = None, passphrase: Optional[str] = None) -> OrderInfo:
        ex = await self._create_exchange(exchange, api_key, api_secret, passphrase)
        try:
            order = await ex.create_order(symbol, order_type, side, amount, price)
            return OrderInfo.from_dict(order)
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise TradingError(str(e))
        finally:
            await ex.close()

    async def close(self) -> None:
        # Nothing persistent to close in this implementation
        return

