# light_trading_bot/src/core/strategy/strategy_manager.py
from .base_strategy import BaseStrategy
import importlib

class StrategyManager:
    def __init__(self, strategy_name: str, config: dict):
        self.strategy_name = strategy_name
        self.config = config
        self.strategy = self.load_strategy()

    def load_strategy(self) -> BaseStrategy:
        try:
            module = importlib.import_module(f"src.core.strategy.{self.strategy_name}")
            return module.Strategy(self.config)
        except Exception as e:
            raise ImportError(f"Failed to load strategy '{self.strategy_name}': {str(e)}")
