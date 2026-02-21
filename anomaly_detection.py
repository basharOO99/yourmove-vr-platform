"""
YourMove — Anomaly Detection Module  v4.0
═══════════════════════════════════════════
Statistical anomaly detection for VR physiological sensor streams.

Detection methods:
  1. Z-Score Detector      — single-sensor deviation from rolling baseline
  2. Spike Detector        — instantaneous jump vs previous frame
  3. Sustained Detector    — prolonged elevation above threshold
  4. Multi-Sensor Detector — correlated elevation across body regions

Output: structured AnomalyEvent objects with severity, confidence, and
clinical context — designed for audit-trail logging in medical systems.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from data_processing import RollingBuffer, SensorProcessor, compute_z_score

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Event dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AnomalyEvent:
    """
    A single detected anomalous condition.
    Designed for structured JSON logging and audit trails.
    """
    sensor:         str
    method:         str           # "z_score" | "spike" | "sustained" | "multi_sensor"
    severity:       str           # "low" | "moderate" | "high" | "critical"
    score:          float         # dimensionless anomaly score ∈ [0, ∞)
    confidence:     float         # detection confidence ∈ [0, 1]
    value:          float         # current observed value
    baseline:       float         # rolling baseline at detection time
    description:    str
    timestamp:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "sensor":      self.sensor,
            "method":      self.method,
            "severity":    self.severity,
            "score":       round(self.score, 3),
            "confidence":  round(self.confidence, 3),
            "value":       round(self.value, 3),
            "baseline":    round(self.baseline, 3),
            "description": self.description,
            "timestamp":   self.timestamp,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Z-Score Anomaly Detector
# ─────────────────────────────────────────────────────────────────────────────

class ZScoreDetector:
    """
    Flags observations that deviate significantly from the rolling mean.

    Thresholds follow clinical signal-processing conventions:
      |z| > 2.0  →  low        (borderline, 1-in-20 by chance under normality)
      |z| > 2.5  →  moderate
      |z| > 3.0  →  high       (1-in-370)
      |z| > 4.0  →  critical   (1-in-15,787)
    """

    LOW_Z      = 2.0
    MODERATE_Z = 2.5
    HIGH_Z     = 3.0
    CRITICAL_Z = 4.0

    def detect(
        self,
        sensor_name: str,
        value: float,
        processor: SensorProcessor,
        signal: str = "stress",   # "stress" | "tremor"
    ) -> Optional[AnomalyEvent]:
        """Return AnomalyEvent if value is anomalous, else None."""

        if signal == "stress":
            z = processor.stress_z(value)
            baseline = processor.stress_mean()
        else:
            z = processor.tremor_z(value)
            baseline = processor.tremor_mean()

        abs_z = abs(z)
        if abs_z < self.LOW_Z:
            return None

        severity = (
            "critical" if abs_z >= self.CRITICAL_Z else
            "high"     if abs_z >= self.HIGH_Z     else
            "moderate" if abs_z >= self.MODERATE_Z else
            "low"
        )

        # Confidence scales with buffer maturity
        confidence = min(1.0, processor.signal_quality().data_maturity * 0.85 + 0.15)

        event = AnomalyEvent(
            sensor=sensor_name,
            method="z_score",
            severity=severity,
            score=abs_z,
            confidence=confidence,
            value=value,
            baseline=baseline,
            description=(
                f"{signal.capitalize()} z-score {abs_z:.2f}σ above rolling baseline "
                f"({baseline:.2f}) in {sensor_name.replace('_', ' ').title()}"
            ),
        )
        logger.debug(
            "z_score_anomaly",
            extra={"anomaly": event.to_dict()}
        )
        return event


# ─────────────────────────────────────────────────────────────────────────────
# Spike Detector
# ─────────────────────────────────────────────────────────────────────────────

class SpikeDetector:
    """
    Detects sudden frame-to-frame jumps (acute stress spikes).
    Complements z-score detection which requires historical context.
    """

    # Minimum absolute jump to qualify (avoids noise triggers)
    MIN_DELTA = 3.0
    # Jump as multiple of rolling std
    STD_MULT_MODERATE = 2.0
    STD_MULT_HIGH     = 3.5
    STD_MULT_CRITICAL = 5.0

    def __init__(self) -> None:
        self._prev: Dict[str, float] = {}

    def detect(
        self,
        sensor_name: str,
        value: float,
        processor: SensorProcessor,
    ) -> Optional[AnomalyEvent]:
        key = sensor_name
        prev = self._prev.get(key)
        self._prev[key] = value

        if prev is None:
            return None

        delta = abs(value - prev)
        if delta < self.MIN_DELTA:
            return None

        std = processor.stress_std()
        if std < 1e-6:
            return None

        ratio = delta / std
        if ratio < self.STD_MULT_MODERATE:
            return None

        severity = (
            "critical" if ratio >= self.STD_MULT_CRITICAL else
            "high"     if ratio >= self.STD_MULT_HIGH     else
            "moderate"
        )
        confidence = min(0.9, ratio / 8.0)

        return AnomalyEvent(
            sensor=sensor_name,
            method="spike",
            severity=severity,
            score=round(ratio, 2),
            confidence=confidence,
            value=value,
            baseline=prev,
            description=(
                f"Acute stress spike in {sensor_name.replace('_', ' ').title()}: "
                f"Δ{delta:.1f} ({ratio:.1f}× rolling std) over 1 frame"
            ),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Sustained Elevation Detector
# ─────────────────────────────────────────────────────────────────────────────

class SustainedDetector:
    """
    Detects sustained elevation above absolute clinical thresholds.
    Tracks how many consecutive frames a sensor exceeds a threshold.
    """

    STRESS_THRESHOLD   = 10.0   # clinical alert threshold
    STRESS_CRITICAL    = 15.0   # imminent-outburst threshold
    TREMOR_THRESHOLD   = 2.5
    TREMOR_CRITICAL    = 5.0

    # Consecutive frames required to trigger
    FRAMES_MODERATE    = 5
    FRAMES_HIGH        = 10
    FRAMES_CRITICAL    = 15

    def __init__(self) -> None:
        self._stress_frames: Dict[str, int] = {}
        self._tremor_frames: Dict[str, int] = {}

    def detect(
        self,
        sensor_name: str,
        stress: float,
        tremor: float,
        stress_timer: float,
    ) -> Optional[AnomalyEvent]:
        """
        stress_timer (from UE5) gives authoritative sustained-stress duration.
        We use it directly when available and > 0.
        """
        # Stress
        if stress >= self.STRESS_THRESHOLD:
            self._stress_frames[sensor_name] = self._stress_frames.get(sensor_name, 0) + 1
        else:
            self._stress_frames[sensor_name] = 0

        # Tremor
        if tremor >= self.TREMOR_THRESHOLD:
            self._tremor_frames[sensor_name] = self._tremor_frames.get(sensor_name, 0) + 1
        else:
            self._tremor_frames[sensor_name] = 0

        sf = self._stress_frames.get(sensor_name, 0)
        tf = self._tremor_frames.get(sensor_name, 0)

        # Prefer UE5 authoritative timer for stress
        duration = max(stress_timer, sf * 0.1)   # assume ~10 Hz

        if stress >= self.STRESS_CRITICAL and duration >= 3.0:
            return AnomalyEvent(
                sensor=sensor_name,
                method="sustained",
                severity="critical",
                score=round(stress / self.STRESS_CRITICAL * 4.0, 2),
                confidence=0.92,
                value=stress,
                baseline=self.STRESS_CRITICAL,
                description=(
                    f"Critical arousal sustained {duration:.1f}s in "
                    f"{sensor_name.replace('_', ' ').title()} — "
                    "immediate clinical intervention required"
                ),
            )

        if tremor >= self.TREMOR_CRITICAL and tf >= self.FRAMES_HIGH:
            return AnomalyEvent(
                sensor=sensor_name,
                method="sustained",
                severity="high",
                score=round(tremor / self.TREMOR_CRITICAL * 3.0, 2),
                confidence=0.85,
                value=tremor,
                baseline=self.TREMOR_CRITICAL,
                description=(
                    f"Severe tremor sustained {tf} frames in "
                    f"{sensor_name.replace('_', ' ').title()}"
                ),
            )

        if stress >= self.STRESS_THRESHOLD and sf >= self.FRAMES_HIGH:
            return AnomalyEvent(
                sensor=sensor_name,
                method="sustained",
                severity="moderate",
                score=round(stress / self.STRESS_THRESHOLD * 2.0, 2),
                confidence=0.75,
                value=stress,
                baseline=self.STRESS_THRESHOLD,
                description=(
                    f"Elevated arousal sustained {sf} frames in "
                    f"{sensor_name.replace('_', ' ').title()}"
                ),
            )

        return None


# ─────────────────────────────────────────────────────────────────────────────
# Multi-Sensor Correlation Detector
# ─────────────────────────────────────────────────────────────────────────────

class MultiSensorDetector:
    """
    Detects global physiological arousal when multiple sensors are
    simultaneously elevated — a hallmark of pre-meltdown state in ASD.
    """

    CORRELATION_THRESHOLD = 0.65   # fraction of sensors above baseline

    def detect(
        self,
        sensor_states: Dict[str, dict],   # name → {"stress": float, "tremor": float}
        processors: Dict[str, SensorProcessor],
    ) -> Optional[AnomalyEvent]:
        n          = len(sensor_states)
        if n == 0:
            return None

        elevated   = sum(
            1 for name, s in sensor_states.items()
            if s["stress"] > processors[name].stress_mean() + processors[name].stress_std()
        )
        ratio = elevated / n

        if ratio < self.CORRELATION_THRESHOLD:
            return None

        severity = "critical" if ratio >= 0.85 else "high" if ratio >= 0.75 else "moderate"
        return AnomalyEvent(
            sensor="global",
            method="multi_sensor",
            severity=severity,
            score=round(ratio * 5.0, 2),
            confidence=round(ratio * 0.9, 2),
            value=ratio,
            baseline=self.CORRELATION_THRESHOLD,
            description=(
                f"Global arousal: {elevated}/{n} sensors ({ratio*100:.0f}%) "
                "simultaneously elevated above individual baselines"
            ),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrated Anomaly Engine
# ─────────────────────────────────────────────────────────────────────────────

class AnomalyEngine:
    """
    Runs all detectors and returns deduplicated, severity-ranked events.
    """

    def __init__(self) -> None:
        self.z_detector         = ZScoreDetector()
        self.spike_detector     = SpikeDetector()
        self.sustained_detector = SustainedDetector()
        self.multi_detector     = MultiSensorDetector()

    def run(
        self,
        sensors_raw: dict,                           # model_dump of AllSensors
        processors:  Dict[str, SensorProcessor],
    ) -> List[AnomalyEvent]:
        """
        Run all detectors against the current frame.
        Returns events sorted by severity (critical first).
        """
        events: List[AnomalyEvent] = []

        sensor_states: Dict[str, dict] = {}

        for name, raw in sensors_raw.items():
            proc = processors.get(name)
            if proc is None:
                continue

            stress = raw["stress_trend"]
            tremor = raw["tremor_intensity"]
            timer  = raw["stress_timer"]
            sensor_states[name] = {"stress": stress, "tremor": tremor}

            # 1. Z-score (stress + tremor)
            ev = self.z_detector.detect(name, stress, proc, "stress")
            if ev:
                events.append(ev)
            ev = self.z_detector.detect(name, tremor, proc, "tremor")
            if ev:
                events.append(ev)

            # 2. Spike
            ev = self.spike_detector.detect(name, stress, proc)
            if ev:
                events.append(ev)

            # 3. Sustained
            ev = self.sustained_detector.detect(name, stress, tremor, timer)
            if ev:
                events.append(ev)

        # 4. Multi-sensor correlation
        ev = self.multi_detector.detect(sensor_states, processors)
        if ev:
            events.append(ev)

        # Deduplicate: keep highest severity per (sensor, method)
        seen:    Dict[Tuple[str, str], AnomalyEvent] = {}
        ORDER    = {"critical": 4, "high": 3, "moderate": 2, "low": 1}
        for ev in events:
            key = (ev.sensor, ev.method)
            if key not in seen or ORDER[ev.severity] > ORDER[seen[key].severity]:
                seen[key] = ev

        return sorted(seen.values(), key=lambda e: -ORDER.get(e.severity, 0))
