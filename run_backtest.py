"""Front door: configure a strategy, run the validation grid."""

from engine.backtest import BacktestEngine
from strategies.sma_crossover import SmaCrossover

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "JPM", "XOM"]

engine = BacktestEngine(starting_cash=10_000, slippage_bps=10)
strategy = SmaCrossover(short_window=10, long_window=30)

engine.run_grid(strategy, symbols=SYMBOLS, years=3)
