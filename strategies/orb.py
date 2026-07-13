"""Opening Range Breakout: buy a break above the opening range high,
stop out below the range low, flat by close (engine enforces)."""

from strategies.base import IntradayStrategy


class OpeningRangeBreakout(IntradayStrategy):
    def __init__(self, range_minutes=15, bar_minutes=5):
        self.opening_bars = range_minutes // bar_minutes
        self.bar_minutes = bar_minutes
        self.name = f"orb_{range_minutes}min"

    def plan_day(self, opening_bars_df):
        return {
            "entry": opening_bars_df["high"].max(),
            "stop": opening_bars_df["low"].min(),
        }
