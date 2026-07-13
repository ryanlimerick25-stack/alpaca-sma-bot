import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

SYMBOL = "AAPL"
SHORT_WINDOW = 10   # days
LONG_WINDOW = 30    # days
STARTING_CASH = 10_000

# --- Get data ---
client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
request = StockBarsRequest(
    symbol_or_symbols=SYMBOL,
    timeframe=TimeFrame.Day,
    start=datetime.now() - timedelta(days=365),  # 1 year for more signal history
)
df = client.get_stock_bars(request).df.reset_index()

# --- Compute signals ---
df["sma_short"] = df["close"].rolling(SHORT_WINDOW).mean()
df["sma_long"] = df["close"].rolling(LONG_WINDOW).mean()

# Signal: 1 = short MA above long MA (be in the market), 0 = out
df["signal"] = (df["sma_short"] > df["sma_long"]).astype(int)

# CRITICAL: shift by 1 day. We only know today's signal after the close,
# so we can't trade on it until tomorrow. Skipping this = lookahead bias,
# the #1 rookie backtesting mistake.
df["position"] = df["signal"].shift(1).fillna(0)

# --- Simulate ---
cash = STARTING_CASH
shares = 0
trades = []

for _, row in df.iterrows():
    price = row["close"]
    if row["position"] == 1 and shares == 0:      # buy signal, not holding
        shares = cash / price
        cash = 0
        trades.append(("BUY", row["timestamp"].date(), round(price, 2)))
    elif row["position"] == 0 and shares > 0:     # sell signal, holding
        cash = shares * price
        shares = 0
        trades.append(("SELL", row["timestamp"].date(), round(price, 2)))

final_value = cash + shares * df.iloc[-1]["close"]

# --- Buy and hold comparison ---
first_valid = df.dropna(subset=["sma_long"]).iloc[0]["close"]
hold_value = STARTING_CASH * (df.iloc[-1]["close"] / first_valid)

# --- Results ---
print(f"Strategy: {SHORT_WINDOW}/{LONG_WINDOW} day SMA crossover on {SYMBOL}")
print(f"Period: {df.iloc[0]['timestamp'].date()} to {df.iloc[-1]['timestamp'].date()}")
print(f"\nTrades ({len(trades)}):")
for action, date, price in trades:
    print(f"  {action:4} {date}  @ ${price}")

print(f"\nStrategy final value:     ${final_value:,.2f}  ({(final_value/STARTING_CASH-1)*100:+.1f}%)")
print(f"Buy-and-hold final value: ${hold_value:,.2f}  ({(hold_value/STARTING_CASH-1)*100:+.1f}%)")
diff = final_value - hold_value
print(f"\nStrategy vs holding: {'+' if diff >= 0 else '-'}${abs(diff):,.2f}")
