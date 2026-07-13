import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
account = trading_client.get_account()
print(f"Account status: {account.status}")
print(f"Paper buying power: ${account.buying_power}")

data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
request = StockLatestQuoteRequest(symbol_or_symbols="AAPL")
quote = data_client.get_stock_latest_quote(request)
aapl = quote["AAPL"]
print(f"AAPL bid: ${aapl.bid_price} / ask: ${aapl.ask_price}")

print("\n✅ Both connections working")
