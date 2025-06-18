# light_trading_bot/src/core/strategy/example_strategy.py
from .base_strategy import BaseStrategy

class Strategy(BaseStrategy):
    def analyze(self, market_data):
        # Example signal logic
        return "BUY" if market_data["rsi"] < 30 else "SELL" if market_data["rsi"] > 70 else "HOLD"

    def should_buy(self, market_data):
        return self.analyze(market_data) == "BUY"

    def should_sell(self, market_data):
        return self.analyze(market_data) == "SELL"
