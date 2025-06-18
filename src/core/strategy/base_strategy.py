# light_trading_bot/src/core/strategy/base_strategy.py
class BaseStrategy:
    def __init__(self, config):
        self.config = config

    def analyze(self, market_data):
        raise NotImplementedError("You must implement the analyze method")

    def should_buy(self, market_data):
        raise NotImplementedError()

    def should_sell(self, market_data):
        raise NotImplementedError()
