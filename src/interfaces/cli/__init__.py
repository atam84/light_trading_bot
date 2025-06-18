# src/interfaces/cli/__init__.py

"""
CLI Interface Package

This package provides command-line interface functionality for the trading bot.
Includes colored output, comprehensive commands, and async operation support.
"""

from .cli_main import cli, TradingBotCLI

__all__ = ['cli', 'TradingBotCLI']
