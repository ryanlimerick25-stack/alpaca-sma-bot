"""Risk management experiment: same strategy, three risk regimes.
Watch the drawdown columns, not just returns."""

from engine.backtest import BacktestEngine
from engine.risk import RiskConfig, NO_RISK
from strategies.sma_crossover import SmaCrossover

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "JPM", "XOM"]
strategy = SmaCrossover(10, 30)

print("### 1. No risk controls (all-in, no stops) ###\n")
BacktestEngine(risk=NO_RISK).run_grid(strategy, SYMBOLS)

print("\n" + "=" * 64 + "\n")
print("### 2. Stop-loss 8%, re-enter only after signal reset ###\n")
BacktestEngine(risk=RiskConfig(stop_loss_pct=8, reenter_after_stop=True)).run_grid(strategy, SYMBOLS)

print("\n" + "=" * 64 + "\n")
print("### 3. Half position size + 20% drawdown kill switch ###\n")
BacktestEngine(risk=RiskConfig(position_fraction=0.5, max_drawdown_pct=20)).run_grid(strategy, SYMBOLS)
