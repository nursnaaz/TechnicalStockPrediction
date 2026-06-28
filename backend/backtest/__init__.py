"""
Backtesting Module

Validates scanner predictions against historical data to measure accuracy.
"""

from .engine import BacktestEngine
from .metrics import BacktestMetrics

__all__ = ["BacktestEngine", "BacktestMetrics"]
