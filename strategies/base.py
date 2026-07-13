"""Strategy interface. Every strategy plugs into the same engine by
implementing generate_signals()."""


class Strategy:
    """Base class for all strategies.

    Subclasses implement generate_signals(df), which takes a DataFrame of
    OHLCV bars and returns the same DataFrame with a 'position' column:
        1 = be in the market
        0 = be out
    The engine handles everything else: fills, slippage, P&L, benchmarks.

    IMPORTANT: generate_signals must not look ahead. If a signal is computed
    from bar N's close, the position change happens at bar N+1. The provided
    helper shift_signals() handles this.
    """

    name = "base"

    def generate_signals(self, df):
        raise NotImplementedError("Strategies must implement generate_signals()")

    @staticmethod
    def shift_signals(df, signal_col="signal"):
        """Convert a same-bar signal into a tradeable next-bar position
        (prevents lookahead bias)."""
        df = df.copy()
        df["position"] = df[signal_col].shift(1).fillna(0)
        return df
