"""Backtest engine: runs any Strategy through a multi-symbol, multi-period
grid with slippage modeling and split-adjusted data."""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()


class BacktestEngine:
    def __init__(self, starting_cash=10_000, slippage_bps=10):
        self.starting_cash = starting_cash
        self.slippage_bps = slippage_bps
        self.client = StockHistoricalDataClient(
            os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
        )

    def get_bars(self, symbol, start, end):
        """Daily bars, split- and dividend-adjusted (critical for honest
        backtests — see the NVDA 10:1 split bug this catches)."""
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            adjustment="all",
        )
        return self.client.get_stock_bars(req).df.reset_index()

    def run_single(self, strategy, df):
        """Run one strategy on one DataFrame of bars."""
        df = strategy.generate_signals(df)
        slip = self.slippage_bps / 10_000

        cash, shares, n_trades = self.starting_cash, 0.0, 0
        for _, row in df.iterrows():
            price = row["close"]
            if row["position"] == 1 and shares == 0:
                fill = price * (1 + slip)
                shares = cash / fill
                cash = 0.0
                n_trades += 1
            elif row["position"] == 0 and shares > 0:
                fill = price * (1 - slip)
                cash = shares * fill
                shares = 0.0
                n_trades += 1

        final = cash + shares * df.iloc[-1]["close"]

        clean = df.dropna()
        bench_start = clean.iloc[0]["close"] if len(clean) else df.iloc[0]["close"]
        hold_return = df.iloc[-1]["close"] / bench_start - 1
        strat_return = final / self.starting_cash - 1

        return {
            "strategy_return": strat_return,
            "hold_return": hold_return,
            "edge": strat_return - hold_return,
            "n_trades": n_trades,
        }

    def run_grid(self, strategy, symbols, years=3, verbose=True):
        """Run strategy across every symbol and each of the last N one-year
        periods. Returns list of result dicts; prints a report if verbose."""
        now = datetime.now()
        periods = []
        for back in range(years, 0, -1):
            start = now - timedelta(days=365 * back)
            end = start + timedelta(days=365)
            periods.append((start, end, f"{start.year}-{end.year}"))

        results = []
        if verbose:
            print(f"Strategy: {strategy.name} | slippage: {self.slippage_bps} bps")
            print(f"{'Symbol':<7} {'Period':<11} {'Strategy':>9} {'Hold':>9} {'Edge':>9} {'Trades':>7}")
            print("-" * 56)

        for symbol in symbols:
            for start, end, label in periods:
                df = self.get_bars(symbol, start, end)
                if len(df) < 60:
                    if verbose:
                        print(f"{symbol:<7} {label:<11} insufficient data")
                    continue
                r = self.run_single(strategy, df)
                r.update(symbol=symbol, period=label)
                results.append(r)
                if verbose:
                    print(f"{symbol:<7} {label:<11} {r['strategy_return']:>+8.1%} "
                          f"{r['hold_return']:>+8.1%} {r['edge']:>+8.1%} {r['n_trades']:>7}")

        if verbose and results:
            wins = sum(1 for r in results if r["edge"] > 0)
            avg = sum(r["edge"] for r in results) / len(results)
            print("-" * 56)
            print(f"\nBeat buy-and-hold in {wins}/{len(results)} tests ({wins/len(results):.0%})")
            print(f"Average edge: {avg:+.1%}")

        return results
