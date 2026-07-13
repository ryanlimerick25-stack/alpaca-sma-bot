"""Backtest engine: runs any Strategy through a multi-symbol, multi-period
grid with slippage modeling, split-adjusted data, and risk management.

Reports max drawdown alongside returns — risk controls are judged by how
they change the left tail, not the average."""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from engine.risk import RiskConfig, NO_RISK

load_dotenv()


class BacktestEngine:
    def __init__(self, starting_cash=10_000, slippage_bps=10, risk: RiskConfig = NO_RISK):
        self.starting_cash = starting_cash
        self.slippage_bps = slippage_bps
        self.risk = risk
        self.client = StockHistoricalDataClient(
            os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
        )

    def get_bars(self, symbol, start, end):
        req = StockBarsRequest(
            symbol_or_symbols=symbol, timeframe=TimeFrame.Day,
            start=start, end=end, adjustment="all",
        )
        return self.client.get_stock_bars(req).df.reset_index()

    def run_single(self, strategy, df):
        df = strategy.generate_signals(df)
        slip = self.slippage_bps / 10_000
        r = self.risk

        cash, shares, n_trades = self.starting_cash, 0.0, 0
        entry_price = None
        stopped = False          # waiting for signal reset after a stop-out
        halted = False           # drawdown kill switch tripped
        peak_equity = self.starting_cash
        max_dd = 0.0

        for _, row in df.iterrows():
            price = row["close"]
            equity = cash + shares * price

            # --- drawdown tracking / kill switch ---
            peak_equity = max(peak_equity, equity)
            dd = 1 - equity / peak_equity
            max_dd = max(max_dd, dd)
            if not halted and r.max_drawdown_pct is not None and dd * 100 >= r.max_drawdown_pct:
                if shares > 0:
                    cash = shares * price * (1 - slip)
                    shares = 0.0
                    n_trades += 1
                halted = True
            if halted:
                continue

            # --- stop-loss ---
            if shares > 0 and r.stop_loss_pct is not None:
                stop_level = entry_price * (1 - r.stop_loss_pct / 100)
                if row["low"] <= stop_level:
                    cash += shares * stop_level * (1 - slip)
                    shares = 0.0
                    n_trades += 1
                    if r.reenter_after_stop:
                        stopped = True
                    continue

            # --- signal-driven entries/exits ---
            if row["position"] == 1 and shares == 0:
                if stopped:
                    continue  # wait for signal reset
                deploy = cash * r.position_fraction
                fill = price * (1 + slip)
                shares = deploy / fill
                cash -= deploy
                entry_price = fill
                n_trades += 1
            elif row["position"] == 0:
                stopped = False
                if shares > 0:
                    cash += shares * price * (1 - slip)
                    shares = 0.0
                    n_trades += 1

        final = cash + shares * df.iloc[-1]["close"]

        # --- buy-and-hold benchmark + its drawdown ---
        clean = df.dropna()
        bench = clean if len(clean) else df
        closes = bench["close"].reset_index(drop=True)
        hold_return = closes.iloc[-1] / closes.iloc[0] - 1
        running_peak = closes.cummax()
        hold_dd = float((1 - closes / running_peak).max())

        strat_return = final / self.starting_cash - 1
        return {
            "strategy_return": strat_return,
            "hold_return": hold_return,
            "edge": strat_return - hold_return,
            "strat_dd": max_dd,
            "hold_dd": hold_dd,
            "n_trades": n_trades,
            "halted": halted,
        }

    def run_grid(self, strategy, symbols, n_periods=3, window_years=1, verbose=True):
        now = datetime.now()
        periods = []
        window = timedelta(days=365 * window_years)
        for back in range(n_periods, 0, -1):
            start = now - window * back
            end = start + window
            periods.append((start, end, f"{start.year}-{end.year}"))

        results = []
        if verbose:
            print(f"Strategy: {strategy.name} | slippage: {self.slippage_bps} bps | risk: {self.risk}")
            print(f"{'Symbol':<7} {'Period':<11} {'Strategy':>9} {'Hold':>9} {'StratDD':>8} {'HoldDD':>7} {'Trades':>7}")
            print("-" * 64)

        for symbol in symbols:
            for start, end, label in periods:
                df = self.get_bars(symbol, start, end)
                if len(df) < 60:
                    if verbose:
                        print(f"{symbol:<7} {label:<11} insufficient data")
                    continue
                res = self.run_single(strategy, df)
                res.update(symbol=symbol, period=label)
                results.append(res)
                if verbose:
                    flag = " HALT" if res["halted"] else ""
                    print(f"{symbol:<7} {label:<11} {res['strategy_return']:>+8.1%} "
                          f"{res['hold_return']:>+8.1%} {res['strat_dd']:>7.1%} "
                          f"{res['hold_dd']:>6.1%} {res['n_trades']:>7}{flag}")

        if verbose and results:
            wins = sum(1 for x in results if x["edge"] > 0)
            avg_edge = sum(x["edge"] for x in results) / len(results)
            avg_sdd = sum(x["strat_dd"] for x in results) / len(results)
            avg_hdd = sum(x["hold_dd"] for x in results) / len(results)
            print("-" * 64)
            print(f"\nBeat buy-and-hold in {wins}/{len(results)} ({wins/len(results):.0%}) | avg edge: {avg_edge:+.1%}")
            print(f"Avg max drawdown — strategy: {avg_sdd:.1%} | buy-and-hold: {avg_hdd:.1%}")

        return results
