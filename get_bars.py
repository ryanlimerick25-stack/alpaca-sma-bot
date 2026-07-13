import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# Last 6 months of daily bars for AAPL
request = StockBarsRequest(
    symbol_or_symbols="AAPL",
    timeframe=TimeFrame.Day,
    start=datetime.now() - timedelta(days=180),
)

bars = client.get_stock_bars(request)
df = bars.df  # converts straight to a pandas DataFrame

print(df.head(10))
print(f"\nTotal bars: {len(df)}")
print(f"Columns: {list(df.columns)}")
