"""
YourMove — Statistical Data Processing Module  v4.0
════════════════════════════════════════════════════
Pure-Python statistical processing for real-time VR sensor streams.
No external numeric dependencies — runs on standard library only.

Provides:
  • RollingBuffer       — fixed-capacity deque with online statistics
  • compute_z_score     — standardized anomaly score
  • compute_trend_slope — least-squares linear regression slope
  • compute_ewma        — exponential weighted moving average
  • SignalQuality       — data completeness & reliability rating
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Sequence, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Rolling buffer with online Welford variance
# ─────────────────────────────────────────────────────────────────────────────

class RollingBuffer:
    """
    Fixed-capacity ring buffer with O(1) push and online mean/variance.

    Uses Welford's online algorithm for numerically stable variance
    (critical for medical signal processing where we cannot afford
     catastrophic cancellation errors at low amplitude).
    """

    def __init__(self, capacity: int = 120) -> None:
        if capacity < 2:
            raise ValueError("Capacity must be ≥ 2")
        self.capacity = capacity
        self._data:   Deque[float] = deque(maxlen=capacity)
        self._times:  Deque[float] = deque(maxlen=capacity)  # epoch seconds

        # Welford online state
        self._n:    int   = 0
        self._mean: float = 0.0
        self._M2:   float = 0.0   # sum of squared deviations

    # ── Mutation ──────────────────────────────────────────────────────────────

    def push(self, value: float, timestamp: Optional[float] = None) -> None:
        """Append a new observation, evicting the oldest when full."""
        if self._n == self.capacity:
            self._remove_oldest()

        ts = timestamp if timestamp is not None else time.monotonic()
        self._data.append(value)
        self._times.append(ts)

        # Welford update
        self._n += 1
        delta        = value - self._mean
        self._mean  += delta / self._n
        delta2       = value - self._mean
        self._M2    += delta * delta2

    def _remove_oldest(self) -> None:
        """Remove oldest value and correct Welford state."""
        if self._n == 0:
            return
        old = self._data[0]   # oldest (deque not yet evicted)
        # Reverse Welford
        old_mean    = (self._mean * self._n - old) / (self._n - 1) if self._n > 1 else 0.0
        self._M2   -= (old - self._mean) * (old - old_mean)
        self._M2    = max(0.0, self._M2)   # numerical guard
        self._mean  = old_mean
        self._n    -= 1

    # ── Statistics ────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return self._n

    @property
    def full(self) -> bool:
        return self._n == self.capacity

    def mean(self) -> float:
        return self._mean if self._n > 0 else 0.0

    def variance(self) -> float:
        return self._M2 / (self._n - 1) if self._n >= 2 else 0.0

    def std(self) -> float:
        return math.sqrt(self.variance())

    def last(self, n: int = 1) -> List[float]:
        """Return the n most-recent values (most recent last)."""
        data = list(self._data)
        return data[-n:] if n < len(data) else data

    def timestamps(self) -> List[float]:
        return list(self._times)

    def values(self) -> List[float]:
        return list(self._data)

    def percentile(self, p: float) -> float:
        """Approximate p-th percentile (0-100) via sorted copy."""
        if not self._data:
            return 0.0
        s = sorted(self._data)
        k = (len(s) - 1) * p / 100.0
        lo, hi = int(k), min(int(k) + 1, len(s) - 1)
        return s[lo] + (s[hi] - s[lo]) * (k - lo)

    def max(self) -> float:
        return max(self._data) if self._data else 0.0

    def min(self) -> float:
        return min(self._data) if self._data else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Statistical functions (pure Python)
# ─────────────────────────────────────────────────────────────────────────────

def compute_z_score(value: float, mean: float, std: float) -> float:
    """
    Standard z-score: how many standard deviations value is from the mean.
    Returns 0.0 when std is effectively zero (no variation in signal).
    Clamped to [-6, 6] to avoid unbounded outputs on signal spikes.
    """
    if std < 1e-9:
        return 0.0
    z = (value - mean) / std
    return max(-6.0, min(6.0, z))


def compute_trend_slope(
    values: Sequence[float],
    timestamps: Optional[Sequence[float]] = None,
) -> Tuple[float, float]:
    """
    Ordinary least-squares linear regression.

    Parameters
    ----------
    values     : ordered observations y_0…y_n
    timestamps : corresponding x values; uses 0,1,2,… if None

    Returns
    -------
    (slope, r_squared)
    slope is in units/step (or units/second when timestamps supplied).
    r_squared ∈ [0, 1] indicates goodness of fit.
    """
    n = len(values)
    if n < 3:
        return 0.0, 0.0

    x = list(timestamps) if timestamps else list(range(n))
    y = list(values)

    sum_x  = sum(x)
    sum_y  = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi * xi for xi in x)

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-12:
        return 0.0, 0.0

    slope     = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # R²
    y_mean  = sum_y / n
    ss_tot  = sum((yi - y_mean) ** 2 for yi in y)
    ss_res  = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))

    if ss_tot < 1e-12:
        r2 = 1.0
    else:
        r2 = max(0.0, 1.0 - ss_res / ss_tot)

    return slope, r2


def compute_ewma(values: Sequence[float], alpha: float = 0.2) -> List[float]:
    """
    Exponential weighted moving average.
    alpha=0.2 → 5-frame smoothing window equivalent.
    """
    if not values:
        return []
    result = [values[0]]
    for v in values[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])
    return result


def compute_ewma_scalar(value: float, prev_ema: float, alpha: float = 0.2) -> float:
    """Single-step EWMA update — O(1), used in online processing."""
    return alpha * value + (1.0 - alpha) * prev_ema


# ─────────────────────────────────────────────────────────────────────────────
# Signal quality rating
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SignalQuality:
    """
    Assesses reliability of the current statistical estimates.
    Propagated to the AI confidence score.
    """
    n_samples:        int   = 0
    required_samples: int   = 30
    variation_ratio:  float = 0.0  # std / mean (coefficient of variation)

    @property
    def data_maturity(self) -> float:
        """0.0 → 1.0 based on buffer fill level."""
        return min(1.0, self.n_samples / self.required_samples)

    @property
    def signal_clarity(self) -> float:
        """1.0 = very stable signal; 0.0 = pure noise."""
        # CV > 2.0 is considered noisy for physiological signals
        return max(0.0, 1.0 - min(1.0, self.variation_ratio / 2.0))

    @property
    def overall(self) -> float:
        """Composite quality score ∈ [0, 1]."""
        return 0.6 * self.data_maturity + 0.4 * self.signal_clarity

    @classmethod
    def from_buffer(cls, buf: RollingBuffer, required: int = 30) -> "SignalQuality":
        mean = buf.mean()
        std  = buf.std()
        cv   = (std / mean) if mean > 1e-6 else 0.0
        return cls(
            n_samples=buf.count,
            required_samples=required,
            variation_ratio=cv,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Per-sensor state container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SensorProcessor:
    """
    Maintains all rolling statistics for one body-part sensor.
    Capacity = 120 frames ≈ 2 minutes at 1 Hz or 12 seconds at 10 Hz.
    """
    capacity: int = 120

    stress_buf: RollingBuffer  = field(default_factory=lambda: RollingBuffer(120))
    tremor_buf: RollingBuffer  = field(default_factory=lambda: RollingBuffer(120))

    ema_stress: float = 0.0
    ema_tremor: float = 0.0
    EMA_ALPHA:  float = 0.15   # slower smoothing = more stable clinical output

    peak_stress: float = 0.0
    peak_tremor: float = 0.0

    alert_frames: int = 0

    def update(self, stress: float, tremor: float, ts: Optional[float] = None) -> None:
        """Ingest a new observation and update all statistics."""
        self.stress_buf.push(stress, ts)
        self.tremor_buf.push(tremor, ts)

        self.ema_stress = compute_ewma_scalar(stress, self.ema_stress, self.EMA_ALPHA)
        self.ema_tremor = compute_ewma_scalar(tremor, self.ema_tremor, self.EMA_ALPHA)

        self.peak_stress = max(self.peak_stress, stress)
        self.peak_tremor = max(self.peak_tremor, tremor)

    # Convenience properties
    def stress_mean(self) -> float: return self.stress_buf.mean()
    def stress_std(self)  -> float: return self.stress_buf.std()
    def tremor_mean(self) -> float: return self.tremor_buf.mean()
    def tremor_std(self)  -> float: return self.tremor_buf.std()

    def stress_z(self, value: float) -> float:
        return compute_z_score(value, self.stress_mean(), self.stress_std())

    def tremor_z(self, value: float) -> float:
        return compute_z_score(value, self.tremor_mean(), self.tremor_std())

    def stress_slope(self) -> Tuple[float, float]:
        """(slope, r²) for stress_trend over the last 30 observations."""
        vals = self.stress_buf.last(30)
        return compute_trend_slope(vals)

    def signal_quality(self) -> SignalQuality:
        return SignalQuality.from_buffer(self.stress_buf, required=30)
