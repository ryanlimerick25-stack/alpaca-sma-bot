"""Generate the README hero chart: strategy vs buy-and-hold equity curves
with drawdowns, on the repo's flagship honest result (AAPL, last year:
strategy +28% vs holding +40%)."""

import os
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")  # no display needed, just write the file
import matplotlib.pyplot as plt

from engine.backtest import BacktestEngine
from strategies.sma_crossover import SmaCrossover

SYMBOL = "AAPL"
STARTING_CASH = 10_000
SLIP = 10 / 10_000

engine = BacktestEngine()
end = datetime.now()
start = end - timedelta(days=365)
df = engine.get_bars(SYMBOL, start, end)
df = SmaCrossover(10, 30).generate_signals(df).reset_index(drop=True)

# --- daily equity curves ---
cash, shares = STARTING_CASH, 0.0
strat_equity, dates = [], []
for _, row in df.iterrows():
    price = row["close"]
    if row["position"] == 1 and shares == 0:
        shares = cash / (price * (1 + SLIP))
        cash = 0.0
    elif row["position"] == 0 and shares > 0:
        cash = shares * price * (1 - SLIP)
        shares = 0.0
    strat_equity.append(cash + shares * price)
    dates.append(row["timestamp"])

hold_equity = (df["close"] / df["close"].iloc[0] * STARTING_CASH).tolist()

def drawdown(series):
    peak, out = series[0], []
    for v in series:
        peak = max(peak, v)
        out.append((v / peak - 1) * 100)
    return out

# --- plot ---
fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(10, 6.5), sharex=True,
    gridspec_kw={"height_ratios": [2.2, 1]},
)

ax1.plot(dates, hold_equity, label="Buy & hold", color="#888888", lw=1.8)
ax1.plot(dates, strat_equity, label="SMA 10/30 crossover", color="#1f6feb", lw=1.8)
ax1.set_ylabel("Equity ($10k start)")
ax1.legend(loc="upper left", frameon=False)
sr = strat_equity[-1] / STARTING_CASH - 1
hr = hold_equity[-1] / STARTING_CASH - 1
ax1.set_title(
    f"{SYMBOL}, last 12 months — strategy {sr:+.0%} vs holding {hr:+.0%}: "
    "the strategy loses, honestly",
    fontsize=11,
)

ax2.fill_between(dates, drawdown(hold_equity), 0, color="#888888", alpha=0.45, label="Buy & hold")
ax2.fill_between(dates, drawdown(strat_equity), 0, color="#1f6feb", alpha=0.45, label="Strategy")
ax2.set_ylabel("Drawdown (%)")
ax2.legend(loc="lower left", frameon=False)

for ax in (ax1, ax2):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.25)

fig.autofmt_xdate()
plt.tight_layout()
plt.savefig("docs/equity_curve.png", dpi=150)
print("wrote docs/equity_curve.png")
