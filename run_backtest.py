"""Front door: configure strategies, run the validation grid.

Rule of thumb: window_years must give the strategy room to trade.
A strategy needs its longest lookback (in trading days) to be a small
fraction of the window, not most of it."""

from engine.backtest import BacktestEngine
from strategies.sma_crossover import SmaCrossover

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "JPM", "XOM"]

engine = BacktestEngine(starting_cash=10_000, slippage_bps=10)

# Fast strategy, short windows: 3 one-year periods
engine.run_grid(SmaCrossover(10, 30), symbols=SYMBOLS, n_periods=3, window_years=1)

print("\n" + "=" * 56 + "\n")

# Slow strategy, long windows: 2 four-year periods (8 years of data)
engine.run_grid(SmaCrossover(50, 200), symbols=SYMBOLS, n_periods=2, window_years=4)
