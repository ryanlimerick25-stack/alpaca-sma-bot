"""Intraday backtest engine: minute bars, per-day execution of
IntradayStrategy plans, always flat by close."""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

load_dotenv()


class IntradayBacktestEngine:
    def __init__(self, starting_cash=10_000, slippage_bps=10, bar_minutes=5):
        self.starting_cash = starting_cash
        self.slippage_bps = slippage_bps
        self.bar_minutes = bar_minutes
        self.client = StockHistoricalDataClient(
            os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
        )

    def get_minute_bars(self, symbol, days_back):
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame(self.bar_minutes, TimeFrameUnit.Minute),
            start=datetime.now() - timedelta(days=days_back),
            adjustment="all",
        )
        df = self.client.get_stock_bars(req).df.reset_index()
        # UTC -> market time, regular hours only (9:30-16:00 ET)
        df["timestamp"] = df["timestamp"].dt.tz_convert("America/New_York")
        df["date"] = df["timestamp"].dt.date
        t = df["timestamp"].dt.time
        open_t = datetime.strptime("09:30", "%H:%M").time()
        close_t = datetime.strptime("16:00", "%H:%M").time()
        return df[(t >= open_t) & (t < close_t)]

    def run_single(self, strategy, df, verbose=False):
        """Run one intraday strategy over grouped daily sessions."""
        slip = self.slippage_bps / 10_000
        cash = self.starting_cash
        daily_results = []

        for date, day in df.groupby("date"):
            day = day.sort_values("timestamp")
            n = strategy.opening_bars
            if len(day) < n + 2:
                continue

            plan = strategy.plan_day(day.iloc[:n])
            if plan is None:
                continue

            shares, entry, day_pnl = 0.0, None, 0.0
            for _, bar in day.iloc[n:].iterrows():
                if shares == 0:
                    if bar["high"] > plan["entry"]:
                        fill = plan["entry"] * (1 + slip)
                        shares = cash / fill
                        entry = fill
                else:
                    if bar["low"] < plan["stop"]:
                        fill = plan["stop"] * (1 - slip)
                        day_pnl = shares * (fill - entry)
                        shares = 0.0
                        break

            if shares > 0:  # flat by close
                fill = day.iloc[-1]["close"] * (1 - slip)
                day_pnl = shares * (fill - entry)
                shares = 0.0

            cash += day_pnl
            if entry is not None:
                daily_results.append((date, day_pnl))

        wins = sum(1 for _, p in daily_results if p > 0)
        total = len(daily_results)
        return {
            "final_value": cash,
            "return": cash / self.starting_cash - 1,
            "days_traded": total,
            "win_rate": wins / total if total else 0.0,
        }

    def run_grid(self, strategy, symbols, days_back=60, verbose=True):
        if verbose:
            print(f"Strategy: {strategy.name} | slippage: {self.slippage_bps} bps | last {days_back} days")
            print(f"{'Symbol':<7} {'Return':>8} {'Days':>6} {'WinRate':>8}")
            print("-" * 34)
        results = []
        for symbol in symbols:
            df = self.get_minute_bars(symbol, days_back)
            if len(df) < 100:
                if verbose:
                    print(f"{symbol:<7} insufficient data")
                continue
            r = self.run_single(strategy, df)
            r["symbol"] = symbol
            results.append(r)
            if verbose:
                print(f"{symbol:<7} {r['return']:>+7.1%} {r['days_traded']:>6} {r['win_rate']:>7.0%}")
        if verbose and results:
            avg = sum(r["return"] for r in results) / len(results)
            print("-" * 34)
            print(f"Average return: {avg:+.1%}")
        return results
