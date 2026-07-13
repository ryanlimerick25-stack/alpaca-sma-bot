"""Simple moving average crossover: long when short SMA > long SMA."""

from strategies.base import Strategy


class SmaCrossover(Strategy):
    name = "sma_crossover"

    def __init__(self, short_window=10, long_window=30):
        self.short_window = short_window
        self.long_window = long_window
        self.name = f"sma_{short_window}_{long_window}"

    def generate_signals(self, df):
        df = df.copy()
        df["sma_short"] = df["close"].rolling(self.short_window).mean()
        df["sma_long"] = df["close"].rolling(self.long_window).mean()
        df["signal"] = (df["sma_short"] > df["sma_long"]).astype(int)
        return self.shift_signals(df)
