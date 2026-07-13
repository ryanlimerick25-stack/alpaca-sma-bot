"""Risk management configuration, applied by the engine to any strategy.

Honest framing: risk controls do not create edge. A losing strategy with
great risk management still loses — slower and more survivably. What these
change is the DISTRIBUTION of outcomes: they cut off the catastrophic left
tail. Judge them by max drawdown, not by return."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskConfig:
    #: exit if a position falls this % below entry (None = off)
    stop_loss_pct: Optional[float] = None

    #: fraction of available cash deployed per entry (1.0 = all-in).
    #: All-in is what naive bots do; no real system does.
    position_fraction: float = 1.0

    #: halt all trading if total equity falls this % from its peak (None = off)
    max_drawdown_pct: Optional[float] = None

    #: after a stop-out, wait for the signal to reset (go flat) before
    #: re-entering — prevents immediate re-entry into the same falling knife
    reenter_after_stop: bool = False


NO_RISK = RiskConfig()  # baseline: all-in, no stops, no kill switch
