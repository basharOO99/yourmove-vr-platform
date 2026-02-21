"""
YourMove — Predictive Stress Model  v4.0
═════════════════════════════════════════
Short-horizon stress forecasting (0–120 seconds ahead) for pre-emptive
clinical intervention in ASD/ADHD VR therapy sessions.

Method
──────
A hybrid of:
  1. Linear trend extrapolation (OLS slope)       — captures directional drift
  2. Exponential weighted moving average forecast  — captures recent momentum
  3. Ensemble blending                             — weighted by R²

The output is NOT a validated ML model — it is a statistically-grounded
clinical support tool that should be interpreted alongside clinical judgement.
This is explicitly communicated to clinicians in the UI.

Uncertainty is quantified via a simple prediction interval derived from
the root-mean-square deviation (RMSD) of the in-sample OLS fit.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from data_processing import (
    RollingBuffer,
    SensorProcessor,
    compute_ewma_scalar,
    compute_trend_slope,
)


# ─────────────────────────────────────────────────────────────────────────────
# Prediction output
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StressPrediction:
    """
    Short-horizon stress forecast for one body-part sensor.
    All values in the same units as stress_trend (raw sensor scale).
    """
    sensor:             str
    horizon_seconds:    int       # e.g. 30, 60, 120
    predicted_value:    float     # point estimate
    lower_bound:        float     # 80% prediction interval lower
    upper_bound:        float     # 80% prediction interval upper
    confidence:         float     # ∈ [0, 1] — model reliability
    trend_direction:    str       # "rising" | "falling" | "stable"
    will_breach:        bool      # predicted to exceed clinical threshold?
    breach_threshold:   float     # threshold used for will_breach
    current_value:      float
    method:             str       # "linear" | "ewma" | "ensemble"
    r_squared:          float

    def to_dict(self) -> dict:
        return {
            "sensor":          self.sensor,
            "horizon_s":       self.horizon_seconds,
            "predicted":       round(self.predicted_value, 2),
            "lower_80":        round(self.lower_bound, 2),
            "upper_80":        round(self.upper_bound, 2),
            "confidence":      round(self.confidence, 3),
            "trend":           self.trend_direction,
            "will_breach":     self.will_breach,
            "threshold":       self.breach_threshold,
            "current":         round(self.current_value, 2),
            "method":          self.method,
            "r2":              round(self.r_squared, 3),
        }


@dataclass
class GlobalPrediction:
    """Session-level forecast aggregated across all sensors."""
    horizon_seconds:        int
    max_predicted_stress:   float
    avg_predicted_stress:   float
    sensors_at_risk:        List[str]      # will breach threshold
    session_risk_trend:     str            # "escalating" | "stable" | "deescalating"
    confidence:             float
    prediction_timestamp:   float = 0.0

    def __post_init__(self):
        if not self.prediction_timestamp:
            self.prediction_timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "horizon_s":             self.horizon_seconds,
            "max_predicted_stress":  round(self.max_predicted_stress,  2),
            "avg_predicted_stress":  round(self.avg_predicted_stress,  2),
            "sensors_at_risk":       self.sensors_at_risk,
            "session_risk_trend":    self.session_risk_trend,
            "confidence":            round(self.confidence, 3),
            "timestamp":             self.prediction_timestamp,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Core predictor
# ─────────────────────────────────────────────────────────────────────────────

class StressPredictor:
    """
    Per-session predictive model.
    Instantiate once per UE5 session; call predict() each frame.
    """

    CLINICAL_THRESHOLD  = 10.0    # stress_trend above which we flag "at risk"
    CRITICAL_THRESHOLD  = 15.0    # critical intervention threshold
    MIN_SAMPLES         = 15      # minimum observations before producing forecast
    HORIZON_S           = 120     # default: 2-minute forecast
    ALT_HORIZONS        = [30, 60, 120]
    # 80% prediction interval z-score
    PI_Z                = 1.282

    def __init__(self) -> None:
        # Track EWMA forecast state per sensor
        self._ewma_forecast: Dict[str, float] = {}

    def predict(
        self,
        sensor_name: str,
        processor:   SensorProcessor,
        horizon_s:   int = HORIZON_S,
        tick_rate:   float = 10.0,   # frames-per-second from UE5
    ) -> Optional[StressPrediction]:
        """
        Produce a horizon-second stress forecast for one sensor.
        Returns None if insufficient data for reliable estimation.
        """
        buf = processor.stress_buf
        if buf.count < self.MIN_SAMPLES:
            return None

        vals   = buf.values()
        n      = len(vals)
        current = vals[-1]

        # ── 1. Linear extrapolation ─────────────────────────────────────────
        slope, r2_linear = compute_trend_slope(vals)
        # Convert slope from frames to seconds
        slope_per_s = slope * tick_rate
        horizon_frames = horizon_s * tick_rate
        linear_pred = current + slope * horizon_frames
        linear_pred = max(0.0, linear_pred)

        # RMSD for prediction interval
        x = list(range(n))
        intercept = buf.mean() - slope * (n - 1) / 2.0
        residuals = [vals[i] - (slope * i + intercept) for i in x]
        rmsd = math.sqrt(sum(r ** 2 for r in residuals) / n) if n > 0 else 1.0
        # Widen PI for longer horizons
        horizon_factor = math.sqrt(1 + horizon_s / 60.0)
        pi_half = self.PI_Z * rmsd * horizon_factor

        # ── 2. EWMA forecast ────────────────────────────────────────────────
        # Adaptive alpha: higher when we see clear trend
        alpha = max(0.1, min(0.4, abs(slope) * 0.5 + 0.1))
        ewma  = self._ewma_forecast.get(sensor_name, current)
        ewma  = compute_ewma_scalar(current, ewma, alpha)
        self._ewma_forecast[sensor_name] = ewma
        # EWMA forecast assumes trend continues with decay
        ewma_pred = ewma + slope_per_s * horizon_s * 0.7   # damped
        ewma_pred = max(0.0, ewma_pred)

        # ── 3. Ensemble blend ───────────────────────────────────────────────
        # Weight by linear R² when it's informative, else equal blend
        if r2_linear > 0.3:
            w_lin  = 0.6 + 0.4 * r2_linear
            w_ewma = 1.0 - w_lin
        else:
            w_lin  = 0.4
            w_ewma = 0.6
        ensemble_pred = w_lin * linear_pred + w_ewma * ewma_pred
        ensemble_pred = max(0.0, ensemble_pred)

        # ── Prediction interval ─────────────────────────────────────────────
        lower = max(0.0, ensemble_pred - pi_half)
        upper = ensemble_pred + pi_half

        # ── Confidence ──────────────────────────────────────────────────────
        data_factor    = min(1.0, buf.count / 60.0)
        r2_factor      = max(0.2, r2_linear)
        noise_factor   = 1.0 - min(1.0, (rmsd / (buf.mean() + 0.1)) * 2.0)
        confidence     = round(0.5 * data_factor + 0.3 * r2_factor + 0.2 * noise_factor, 3)
        confidence     = max(0.05, min(0.95, confidence))

        # ── Trend direction ─────────────────────────────────────────────────
        slope_threshold = 0.02   # per frame
        if slope > slope_threshold:
            trend = "rising"
        elif slope < -slope_threshold:
            trend = "falling"
        else:
            trend = "stable"

        # ── Breach assessment ───────────────────────────────────────────────
        threshold    = self.CRITICAL_THRESHOLD if current > self.CLINICAL_THRESHOLD else self.CLINICAL_THRESHOLD
        will_breach  = ensemble_pred >= threshold and upper >= threshold

        method = "ensemble" if r2_linear > 0.1 else "ewma"

        return StressPrediction(
            sensor=sensor_name,
            horizon_seconds=horizon_s,
            predicted_value=round(ensemble_pred, 3),
            lower_bound=round(lower, 3),
            upper_bound=round(upper, 3),
            confidence=confidence,
            trend_direction=trend,
            will_breach=will_breach,
            breach_threshold=threshold,
            current_value=round(current, 3),
            method=method,
            r_squared=round(r2_linear, 3),
        )

    def predict_global(
        self,
        processors: Dict[str, SensorProcessor],
        horizon_s:  int = HORIZON_S,
    ) -> Optional[GlobalPrediction]:
        """
        Aggregate per-sensor predictions into a session-level forecast.
        """
        predictions = []
        for name, proc in processors.items():
            p = self.predict(name, proc, horizon_s)
            if p:
                predictions.append(p)

        if not predictions:
            return None

        predicted_vals  = [p.predicted_value for p in predictions]
        at_risk         = [p.sensor for p in predictions if p.will_breach]
        avg_conf        = sum(p.confidence for p in predictions) / len(predictions)

        # Session trend: majority-vote on individual sensor trends
        counts = {"rising": 0, "falling": 0, "stable": 0}
        for p in predictions:
            counts[p.trend_direction] += 1

        if counts["rising"] > counts["falling"] and counts["rising"] > counts["stable"]:
            session_trend = "escalating"
        elif counts["falling"] > counts["rising"] and counts["falling"] > counts["stable"]:
            session_trend = "de-escalating"
        else:
            session_trend = "stable"

        return GlobalPrediction(
            horizon_seconds=horizon_s,
            max_predicted_stress=round(max(predicted_vals), 2),
            avg_predicted_stress=round(sum(predicted_vals) / len(predicted_vals), 2),
            sensors_at_risk=at_risk,
            session_risk_trend=session_trend,
            confidence=round(avg_conf, 3),
        )

    def predict_all_horizons(
        self,
        processors: Dict[str, SensorProcessor],
    ) -> Dict[int, Optional[GlobalPrediction]]:
        """Return predictions at all standard horizons (30s, 60s, 120s)."""
        return {h: self.predict_global(processors, h) for h in self.ALT_HORIZONS}
