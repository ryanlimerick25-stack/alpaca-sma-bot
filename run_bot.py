import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

SYMBOL = "AAPL"
SHORT_WINDOW = 10
LONG_WINDOW = 30
TRADE_CASH = 10_000  # max dollars to deploy per position

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# --- 1. Compute today's signal from recent daily bars ---
request = StockBarsRequest(
    symbol_or_symbols=SYMBOL,
    timeframe=TimeFrame.Day,
    start=datetime.now() - timedelta(days=90),
)
df = data_client.get_stock_bars(request).df.reset_index()

sma_short = df["close"].rolling(SHORT_WINDOW).mean().iloc[-1]
sma_long = df["close"].rolling(LONG_WINDOW).mean().iloc[-1]
signal = 1 if sma_short > sma_long else 0

print(f"{SYMBOL} | SMA{SHORT_WINDOW}: ${sma_short:.2f} | SMA{LONG_WINDOW}: ${sma_long:.2f}")
print(f"Signal: {'IN (bullish)' if signal else 'OUT (bearish)'}")

# --- 2. Check current position ---
positions = {p.symbol: p for p in trading_client.get_all_positions()}
holding = SYMBOL in positions
if holding:
    pos = positions[SYMBOL]
    print(f"Current position: {pos.qty} shares, market value ${float(pos.market_value):,.2f}")
else:
    print("Current position: none")

# --- 3. Act only if signal and position disagree ---
clock = trading_client.get_clock()
if not clock.is_open:
    print(f"\nMarket is CLOSED (next open: {clock.next_open}). No orders placed.")
elif signal == 1 and not holding:
    latest_price = df.iloc[-1]["close"]
    qty = int(TRADE_CASH / latest_price)
    order = trading_client.submit_order(MarketOrderRequest(
        symbol=SYMBOL, qty=qty, side=OrderSide.BUY, time_in_force=TimeInForce.DAY,
    ))
    print(f"\n>>> BUY order submitted: {qty} shares of {SYMBOL} (order id: {order.id})")
elif signal == 0 and holding:
    order = trading_client.close_position(SYMBOL)
    print(f"\n>>> SELL order submitted: closing {SYMBOL} position")
else:
    print("\nSignal and position agree — nothing to do.")
