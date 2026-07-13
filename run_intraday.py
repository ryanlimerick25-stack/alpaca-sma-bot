"""Front door for intraday strategies."""

from engine.intraday import IntradayBacktestEngine
from strategies.orb import OpeningRangeBreakout

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "JPM", "XOM"]

engine = IntradayBacktestEngine(starting_cash=10_000, slippage_bps=10, bar_minutes=5)
strategy = OpeningRangeBreakout(range_minutes=15)

engine.run_grid(strategy, symbols=SYMBOLS, days_back=60)
