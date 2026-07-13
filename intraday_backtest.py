import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

load_dotenv()
client = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))

SYMBOL = "AAPL"
DAYS_BACK = 60          # ~2 months of trading days
OPEN_RANGE_MIN = 15     # opening range = first 15 minutes
STARTING_CASH = 10_000
SLIPPAGE_BPS = 10

# --- Pull 5-minute bars ---
req = StockBarsRequest(
    symbol_or_symbols=SYMBOL,
    timeframe=TimeFrame(5, TimeFrameUnit.Minute),
    start=datetime.now() - timedelta(days=DAYS_BACK),
    adjustment="all",
)
df = client.get_stock_bars(req).df.reset_index()

# Convert to US market time and keep regular hours only (9:30-16:00 ET)
df["timestamp"] = df["timestamp"].dt.tz_convert("America/New_York")
df["date"] = df["timestamp"].dt.date
df["time"] = df["timestamp"].dt.time
df = df[(df["time"] >= datetime.strptime("09:30", "%H:%M").time()) &
        (df["time"] <  datetime.strptime("16:00", "%H:%M").time())]

slip = SLIPPAGE_BPS / 10_000
cash = STARTING_CASH
daily_results = []

for date, day in df.groupby("date"):
    day = day.sort_values("timestamp")
    # Opening range = first N minutes (three 5-min bars for 15 min)
    n_bars = OPEN_RANGE_MIN // 5
    if len(day) < n_bars + 2:
        continue
    or_high = day.iloc[:n_bars]["high"].max()
    or_low  = day.iloc[:n_bars]["low"].min()

    position_shares = 0
    entry = None
    day_pnl = 0.0

    for _, bar in day.iloc[n_bars:].iterrows():
        if position_shares == 0:
            # Breakout above opening range -> buy
            if bar["high"] > or_high:
                fill = or_high * (1 + slip)        # assume fill at breakout level + slippage
                position_shares = cash / fill
                entry = fill
        else:
            # Stop: price falls back below the range low
            if bar["low"] < or_low:
                fill = or_low * (1 - slip)
                day_pnl = position_shares * (fill - entry)
                position_shares = 0
                break

    # Flat by close: exit at last bar if still holding
    if position_shares > 0:
        fill = day.iloc[-1]["close"] * (1 - slip)
        day_pnl = position_shares * (fill - entry)
        position_shares = 0

    cash += day_pnl
    if entry is not None:
        daily_results.append((date, day_pnl))

# --- Results ---
wins = sum(1 for _, p in daily_results if p > 0)
total = len(daily_results)
print(f"ORB backtest: {SYMBOL}, {OPEN_RANGE_MIN}-min opening range, {DAYS_BACK} calendar days")
print(f"Days traded: {total} | Win rate: {wins}/{total} ({wins/max(total,1):.0%})")
print(f"Final value: ${cash:,.2f} ({(cash/STARTING_CASH-1)*100:+.1f}%)")
best = max(daily_results, key=lambda x: x[1], default=None)
worst = min(daily_results, key=lambda x: x[1], default=None)
if best:  print(f"Best day:  {best[0]}  {best[1]:+,.2f}")
if worst: print(f"Worst day: {worst[0]}  {worst[1]:+,.2f}")
