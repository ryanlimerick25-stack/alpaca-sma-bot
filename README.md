# Trading Bot — SMA Crossover on Alpaca (Paper)

An end-to-end algorithmic trading pipeline built as a learning project. Runs
entirely on Alpaca paper trading — no real money.

## Architecture

Data feed -> Signal logic -> Execution -> Backtesting

- **test_connection.py** — verifies Trading API + Market Data API access
- **get_bars.py** — pulls historical OHLCV bars into a pandas DataFrame
- **backtest.py** — simulates a 10/30-day SMA crossover strategy against
  1 year of daily data, vs. a buy-and-hold benchmark
- **run_bot.py** — computes the live signal, checks the current position,
  and places a paper order only when signal and position disagree
  (idempotent + stateless: safe to run on a schedule)

## Backtest results (honest version)

Tested on AAPL, Jul 2025 - Jul 2026:

- SMA crossover strategy: +28.6%
- Buy and hold: +38.8%

**The strategy underperformed doing nothing by ~$1,028 on $10k.** Whipsaw
trades and time out of the market during an uptrend ate the edge. The
backtest is also optimistic — it assumes zero commissions and zero slippage
(observed slippage on the first live paper fill: $0.34/share).

Key implementation detail: signals are shifted by one day (shift(1)) to
avoid lookahead bias — today's moving average uses today's close, which
isn't knowable until after the market closes.

## Setup

    pip install alpaca-py python-dotenv pandas
    cp .env.example .env   # add your Alpaca paper keys
    python3 test_connection.py

## Roadmap

- [ ] Multi-symbol, multi-period backtesting with cost/slippage modeling
- [ ] Risk management: position sizing, stop-loss, max drawdown limit
- [ ] Scheduled daily runs + trade logging
- [ ] ML-based signal (walk-forward validated)
