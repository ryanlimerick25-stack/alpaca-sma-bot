import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()
client = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "JPM", "XOM"]
SHORT_WINDOW = 10
LONG_WINDOW = 30
STARTING_CASH = 10_000
SLIPPAGE_BPS = 10  # 0.10% per trade, based on observed live fill

def run_backtest(df):
    """SMA crossover backtest with slippage. Returns (strategy_return, hold_return, n_trades)."""
    df = df.copy()
    df["sma_short"] = df["close"].rolling(SHORT_WINDOW).mean()
    df["sma_long"] = df["close"].rolling(LONG_WINDOW).mean()
    df["signal"] = (df["sma_short"] > df["sma_long"]).astype(int)
    df["position"] = df["signal"].shift(1).fillna(0)  # no lookahead

    slip = SLIPPAGE_BPS / 10_000
    cash, shares, n_trades = STARTING_CASH, 0, 0

    for _, row in df.iterrows():
        price = row["close"]
        if row["position"] == 1 and shares == 0:
            fill = price * (1 + slip)          # buy fills slightly high
            shares = cash / fill
            cash = 0
            n_trades += 1
        elif row["position"] == 0 and shares > 0:
            fill = price * (1 - slip)          # sell fills slightly low
            cash = shares * fill
            shares = 0
            n_trades += 1

    final = cash + shares * df.iloc[-1]["close"]
    strat_ret = final / STARTING_CASH - 1

    valid = df.dropna(subset=["sma_long"])
    hold_ret = valid.iloc[-1]["close"] / valid.iloc[0]["close"] - 1
    return strat_ret, hold_ret, n_trades

# --- Define 3 one-year test periods ---
now = datetime.now()
periods = []
for years_back in (3, 2, 1):
    start = now - timedelta(days=365 * years_back)
    end = start + timedelta(days=365)
    periods.append((start, end, f"{start.year}-{end.year}"))

# --- Run the grid ---
results = []
print(f"{'Symbol':<7} {'Period':<11} {'Strategy':>9} {'Hold':>9} {'Edge':>9} {'Trades':>7}")
print("-" * 56)

for symbol in SYMBOLS:
    for start, end, label in periods:
        req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day,
                               start=start, end=end, adjustment="all")
        df = client.get_stock_bars(req).df.reset_index()
        if len(df) < LONG_WINDOW + 10:
            print(f"{symbol:<7} {label:<11} insufficient data")
            continue
        strat, hold, n = run_backtest(df)
        edge = strat - hold
        results.append(edge)
        print(f"{symbol:<7} {label:<11} {strat:>+8.1%} {hold:>+8.1%} {edge:>+8.1%} {n:>7}")

# --- Summary ---
wins = sum(1 for e in results if e > 0)
print("-" * 56)
print(f"\nStrategy beat buy-and-hold in {wins} of {len(results)} tests ({wins/len(results):.0%})")
print(f"Average edge vs holding: {sum(results)/len(results):+.1%}")
