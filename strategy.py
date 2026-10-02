"""
Trading Strategy Module
Decides trade direction, filtering bad risk/reward odds, and calculating deterministic round slots.
"""
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional

class PredictionStrategy:
    def __init__(self, base_hour: int = 12, base_min: int = 0, base_round: int = 11, max_cents: float = 70.0):
        self.base_hour = base_hour
        self.base_min = base_min
        self.base_round = base_round
        self.max_cents = max_cents

    def get_current_round(self, dt: Optional[datetime] = None) -> int:
        if dt is None:
            dt = datetime.now(timezone.utc)
        diff_minutes = (dt.hour - self.base_hour) * 60 + (dt.minute - self.base_min)
        round_offset = diff_minutes // 15
        return self.base_round + round_offset

    def get_round_times(self, dt: Optional[datetime] = None) -> Tuple[str, str, str, str]:
        """
        Returns (current_start, current_end, prev_start, prev_end) in local WIB (UTC+7).
        """
        if dt is None:
            dt = datetime.now(timezone.utc)
        wib_now = dt + timedelta(hours=7)
        slot_min = (dt.minute // 15) * 15
        
        cur_start = wib_now.replace(minute=slot_min, second=0).strftime("%H:%M")
        cur_end = (wib_now.replace(minute=slot_min, second=0) + timedelta(minutes=15)).strftime("%H:%M")
        prev_end = cur_start
        prev_start = (wib_now.replace(minute=slot_min, second=0) - timedelta(minutes=15)).strftime("%H:%M")
        return cur_start, cur_end, prev_start, prev_end

    def decide(self, spot_price: Optional[float], target_price: Optional[float], momentum: float, rsi: float) -> Tuple[str, str]:
        """
        Momentum & TWAP divergence logic.
        """
        if spot_price is None or target_price is None:
            return "SKIP", "Missing live price feed."

        diff = spot_price - target_price
        
        if diff > 0.3:
            return "UP", f"Spot leading target by +${diff:.2f}"
        elif diff < -0.3:
            return "DOWN", f"Spot lagging target by ${diff:.2f}"
        else:
            # Fallback to momentum
            if momentum >= 0 and rsi < 70:
                return "UP", f"Tight gap ({diff:+.2f}), positive 5m momentum ({momentum:+.2f})"
            else:
                return "DOWN", f"Tight gap ({diff:+.2f}), negative 5m momentum ({momentum:+.2f})"
