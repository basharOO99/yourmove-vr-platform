
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from schemas import AICommand, VRSensorInput

from anomaly_detection import AnomalyEngine, AnomalyEvent
from data_processing import SensorProcessor, compute_trend_slope
from predictive_model import GlobalPrediction, StressPredictor, StressPrediction


# Structured AI audit logger
_ai_logger = logging.getLogger("yourmove.ai")


def _log_decision(event: str, payload: dict) -> None:
    """Emit a structured JSON log line for AI decisions."""
    _ai_logger.info(
        json.dumps({
            "event":     event,
            "ts":        time.time(),
            **payload,
        })
    )


# Clinical body-part display names


BODY_PART_NAMES: Dict[str, str] = {
    "head":            "Head / Cranium",
    "chest":           "Thorax / Chest",
    "hip":             "Pelvis / Hip",
    "left_hand":       "Left Hand",
    "right_hand":      "Right Hand",
    "left_upper_arm":  "L. Proximal Arm",
    "right_upper_arm": "R. Proximal Arm",
    "left_lower_arm":  "L. Forearm",
    "right_lower_arm": "R. Forearm",
    "left_upper_leg":  "L. Proximal Leg",
    "right_upper_leg": "R. Proximal Leg",
    "left_lower_leg":  "L. Distal Leg",
    "right_lower_leg": "R. Distal Leg",
}


# Clinical action map


_CLINICAL_ACTIONS: Dict[str, str] = {
    "continue":          "Continue current protocol. All metrics within normal range.",
    "monitor":           "Increase observation frequency. Arousal trend rising.",
    "slow_down":         "Reduce task complexity. Elevated arousal detected — prevent escalation.",
    "pause_and_breathe": "Initiate structured breathing exercise. Significant tremor or arousal.",
    "calm_down":         "Activate full calming protocol. Consider session pause.",
    "disengage":         "STOP SESSION. Patient disengaged. Alert supervising clinician.",
}

_SEVERITY_ORDER = {"critical": 4, "high": 3, "moderate": 2, "low": 1}



# MovementAnalyzer — main entry point


class MovementAnalyzer:
    """
    Full clinical AI pipeline for YourMove VR sensor streams.

    Per-frame pipeline:
      1. Ingest raw sensor frame → update rolling buffers (data_processing)
      2. Detect anomalies across all sensors   (anomaly_detection)
      3. Classify risk and compute stability   (internal)
      4. Forecast 30/60/120s ahead             (predictive_model)
      5. Generate AICommand for UE5            (this module)
      6. Emit structured audit log             (this module)
    """

    # ── Detection thresholds (absolute — for initial frames) ──────────────────
    STRESS_CRITICAL  = 15.0
    STRESS_ELEVATED  = 10.0
    STRESS_TIMER_MIN = 3.0
    TREMOR_SEVERE    = 5.0
    TREMOR_MILD      = 2.5
    FOCUS_LOW        = 0.6
    FOCUS_CRITICAL   = 0.35

    def __init__(self) -> None:
        self._processors:  Dict[str, SensorProcessor] = {
            name: SensorProcessor() for name in BODY_PART_NAMES
        }
        self._anomaly_engine  = AnomalyEngine()
        self._predictor       = StressPredictor()
        self._session_start   = time.time()
        self._frame_count     = 0
        self._escalation:     int = 0   # 0–3

    # ── Primary entry point 

    def analyze_movement(self, data: VRSensorInput) -> AICommand:
        """
        Ingest one sensor frame, run the full pipeline, return UE5 command.
        Side effects: updates rolling buffers, emits audit log.
        """
        self._frame_count += 1
        sensors = data.sensors.model_dump()
        focus   = data.global_metrics.hmd_eye_dot_product
        ts      = time.time()

        # ── Step 1: Update processors 
        for name, raw in sensors.items():
            proc = self._processors.get(name)
            if proc:
                proc.update(raw["stress_trend"], raw["tremor_intensity"], ts)

        # ── Step 2: Focus check (global override)
        if focus < self.FOCUS_CRITICAL:
            self._escalation = min(3, self._escalation + 1)
            cmd = AICommand(
                command="disengage",
                target_sensor="hmd",
                reason=f"Eye-focus index {focus:.3f} below disengagement threshold ({self.FOCUS_CRITICAL}). {_CLINICAL_ACTIONS['disengage']}",
                severity="critical",
            )
            _log_decision("ai_command", {"command": cmd.command, "severity": cmd.severity, "trigger": "focus_critical", "focus": focus})
            return cmd

        if focus < self.FOCUS_LOW:
            cmd = AICommand(
                command="pause_and_breathe",
                target_sensor="hmd",
                reason=f"Attention drift — focus {focus:.3f} (threshold {self.FOCUS_LOW}). {_CLINICAL_ACTIONS['pause_and_breathe']}",
                severity="medium",
            )
            _log_decision("ai_command", {"command": cmd.command, "severity": cmd.severity, "trigger": "focus_low", "focus": focus})
            return cmd

        # ── Step 3: Anomaly detection 
        anomalies = self._anomaly_engine.run(sensors, self._processors)

        # ── Step 4: Command selection based on anomalies 
        if anomalies:
            top = anomalies[0]
            if top.severity == "critical":
                self._escalation = min(3, self._escalation + 1)
                sev = "critical" if self._escalation >= 2 else "high"
                cmd = AICommand(
                    command="calm_down",
                    target_sensor=top.sensor,
                    reason=f"{top.description} [z={top.score:.2f}, conf={top.confidence:.0%}]. {_CLINICAL_ACTIONS['calm_down']}",
                    severity=sev,
                )
            elif top.severity == "high":
                self._escalation = max(0, self._escalation)
                cmd = AICommand(
                    command="pause_and_breathe",
                    target_sensor=top.sensor,
                    reason=f"{top.description}. {_CLINICAL_ACTIONS['pause_and_breathe']}",
                    severity="high",
                )
            elif top.severity == "moderate":
                self._escalation = max(0, self._escalation - 1)
                cmd = AICommand(
                    command="slow_down",
                    target_sensor=top.sensor,
                    reason=f"{top.description}. {_CLINICAL_ACTIONS['slow_down']}",
                    severity="medium",
                )
            else:
                self._escalation = max(0, self._escalation - 1)
                cmd = AICommand(
                    command="monitor",
                    target_sensor=top.sensor,
                    reason=f"{top.description}. {_CLINICAL_ACTIONS['monitor']}",
                    severity="low",
                )
        else:
            self._escalation = max(0, self._escalation - 1)
            cmd = AICommand(
                command="continue",
                target_sensor=None,
                reason=_CLINICAL_ACTIONS["continue"],
                severity="low",
            )

        _log_decision("ai_command", {
            "command":       cmd.command,
            "severity":      cmd.severity,
            "anomalies":     len(anomalies),
            "escalation":    self._escalation,
            "frame":         self._frame_count,
            "focus":         round(focus, 3),
        })

        return cmd

    # ── Body map status 

    def get_body_part_status(self, data: VRSensorInput) -> Dict[str, dict]:
        sensors = data.sensors.model_dump()
        status: Dict[str, dict] = {}
        for name, proc in self._processors.items():
            raw = sensors.get(name, {})
            s   = raw.get("stress_trend", 0.0)
            t   = raw.get("tremor_intensity", 0.0)

            # Use EMA-smoothed values for colour stability
            es = proc.ema_stress
            et = proc.ema_tremor

            # Z-score for contextual colouring
            sz = abs(proc.stress_z(s))

            if (es > self.STRESS_CRITICAL and raw.get("stress_timer", 0) > self.STRESS_TIMER_MIN) or sz >= 4.0:
                color = "critical"
            elif et > self.TREMOR_SEVERE or sz >= 3.0:
                color = "warning"
            elif es > self.STRESS_ELEVATED or sz >= 2.0:
                color = "elevated"
            elif et > self.TREMOR_MILD or es > 5.0:
                color = "mild"
            else:
                color = "normal"

            slope, r2 = proc.stress_slope()
            status[name] = {
                "name":         BODY_PART_NAMES[name],
                "color":        color,
                "stress_trend": round(proc.ema_stress, 2),
                "tremor":       round(proc.ema_tremor, 2),
                "stress_timer": round(raw.get("stress_timer", 0), 2),
                "speed":        round(raw.get("average_speed", 0), 2),
                "stress_mean":  round(proc.stress_mean(), 2),
                "stress_std":   round(proc.stress_std(), 2),
                "stress_z":     round(proc.stress_z(s), 2),
                "slope":        round(slope, 4),
                "peak_stress":  round(proc.peak_stress, 2),
                "peak_tremor":  round(proc.peak_tremor, 2),
                "alert_frames": proc.alert_frames,
            }
        return status

    # Global stats 

    def get_global_stats(self, data: VRSensorInput) -> Dict[str, float]:
        sensors = data.sensors.model_dump()
        stresses = [v["stress_trend"]     for v in sensors.values()]
        tremors  = [v["tremor_intensity"] for v in sensors.values()]
        return {
            "max_stress":  round(max(stresses),                 2),
            "avg_stress":  round(sum(stresses) / len(stresses), 2),
            "max_tremor":  round(max(tremors),                  2),
            "avg_tremor":  round(sum(tremors)  / len(tremors),  2),
            "focus_level": round(data.global_metrics.hmd_eye_dot_product, 3),
        }

    # Full advanced analytics payload 

    def get_advanced_analytics(self, data: VRSensorInput) -> Dict[str, Any]:
        """
        Returns the complete clinical analytics payload consumed by the dashboard.
        Includes stability index, risk classification, confidence, predictions,
        anomalies, trend, top affected regions, and session summary.
        """
        focus      = data.global_metrics.hmd_eye_dot_product
        gs         = self.get_global_stats(data)
        max_stress = gs["max_stress"]
        max_tremor = gs["max_tremor"]
        avg_stress = gs["avg_stress"]

        # ── Stability Index (0-100) 
        # Composite: focus (35%) + stress deviation from calm (40%) + tremor (25%)
        focus_sc  = focus * 35.0
        stress_sc = max(0.0, 40.0 * (1.0 - avg_stress / 20.0))
        tremor_sc = max(0.0, 25.0 * (1.0 - max_tremor / 10.0))
        stability = round(min(100.0, max(0.0, focus_sc + stress_sc + tremor_sc)), 1)

        # ── Risk Classification 
        if focus < self.FOCUS_CRITICAL or max_stress > 18.0 or max_tremor > 8.0:
            risk = "CRITICAL"
        elif focus < self.FOCUS_LOW or max_stress >= self.STRESS_CRITICAL or max_tremor >= self.TREMOR_SEVERE:
            risk = "HIGH"
        elif max_stress >= self.STRESS_ELEVATED or max_tremor >= self.TREMOR_MILD:
            risk = "MODERATE"
        else:
            risk = "LOW"

        # Confidence Score 
        avg_qual     = sum(p.signal_quality().overall for p in self._processors.values()) / len(self._processors)
        signal_boost = min(0.3, (max_stress / 20.0 + max_tremor / 10.0) * 0.15)
        confidence   = round(min(0.97, avg_qual * 0.7 + signal_boost), 3)

        # Anomalies (lightweight re-run without side effects) 
        sensors      = data.sensors.model_dump()
        anomalies    = self._anomaly_engine.run(sensors, self._processors)
        anomaly_list = [e.to_dict() for e in anomalies[:5]]

        #  Trend analysis 
        # Use global stress buffer (aggregate across all processors)
        recent_stresses = [proc.stress_buf.last(10) for proc in self._processors.values()]
        all_recent = [s for buf in recent_stresses for s in buf]
        trend_slope, trend_r2 = compute_trend_slope(all_recent[-30:]) if len(all_recent) >= 6 else (0.0, 0.0)
        if trend_slope > 0.05:
            trend_direction = "rising"
        elif trend_slope < -0.05:
            trend_direction = "falling"
        else:
            trend_direction = "stable"

        #  Predictive model (120s)
        pred_global = self._predictor.predict_global(self._processors, 120)
        pred_60     = self._predictor.predict_global(self._processors, 60)
        pred_30     = self._predictor.predict_global(self._processors, 30)

        # Top Affected Regions 
        region_scores: List[Dict] = []
        for name, proc in self._processors.items():
            composite = (proc.ema_stress / 20.0) * 60 + (proc.ema_tremor / 10.0) * 40
            region_scores.append({
                "name":        BODY_PART_NAMES[name],
                "key":         name,
                "score":       round(composite, 1),
                "ema_stress":  round(proc.ema_stress, 2),
                "ema_tremor":  round(proc.ema_tremor, 2),
                "peak_stress": round(proc.peak_stress, 2),
                "slope":       round(proc.stress_slope()[0] * 100, 2),  # scaled
                "std":         round(proc.stress_std(), 2),
            })
        top_regions = sorted(region_scores, key=lambda x: -x["score"])[:5]

        # Session Summary 
        duration_s  = round(time.time() - self._session_start, 1)
        summary     = self._generate_summary(risk, stability, trend_direction,
                                              max_stress, max_tremor, focus,
                                              anomalies, pred_global, duration_s)

        return {
            "stability_index":      stability,
            "risk_classification":  risk,
            "confidence_score":     confidence,
            "trend_direction":      trend_direction,
            "trend_slope":          round(trend_slope, 4),
            "trend_r2":             round(trend_r2, 3),
            "anomalies":            anomaly_list,
            "anomaly_count":        len(anomalies),
            "top_affected_regions": top_regions,
            "prediction_120s":      pred_global.to_dict() if pred_global else None,
            "prediction_60s":       pred_60.to_dict()     if pred_60     else None,
            "prediction_30s":       pred_30.to_dict()     if pred_30     else None,
            "session_duration_s":   duration_s,
            "frame_count":          self._frame_count,
            "escalation_level":     self._escalation,
            "session_summary":      summary,
            "clinical_action":      self._clinical_action(risk),
        }

    # Session summary generator 

    def _generate_summary(
        self,
        risk: str, stability: float, trend: str,
        max_stress: float, max_tremor: float, focus: float,
        anomalies: List[AnomalyEvent],
        pred: Optional[GlobalPrediction],
        duration_s: float,
    ) -> str:
        mm   = int(duration_s // 60)
        ss   = int(duration_s % 60)
        dur  = f"{mm}m {ss}s"
        n_an = len(anomalies)
        pred_str = ""
        if pred and pred.confidence > 0.3:
            pred_str = (
                f" Model projects {pred.session_risk_trend} arousal over "
                f"the next {pred.horizon_seconds}s "
                f"(confidence {pred.confidence:.0%})."
            )

        high_regions = [a.sensor.replace("_", " ") for a in anomalies if a.severity in ("critical", "high")][:2]
        region_str   = f" Highest activity in: {', '.join(high_regions)}." if high_regions else ""

        return (
            f"Session duration: {dur}. "
            f"Risk level: {risk}. "
            f"Stability Index: {stability}/100. "
            f"Arousal trend {trend}; max stress {max_stress:.1f}, max tremor {max_tremor:.1f}. "
            f"Focus index {focus:.2f}. "
            f"{n_an} statistical anomal{'y' if n_an == 1 else 'ies'} detected.{region_str}{pred_str}"
        )

    def _clinical_action(self, risk: str) -> str:
        mapping = {
            "CRITICAL": "IMMEDIATE ACTION: Suspend session. Initiate calming protocol. Alert supervising clinician.",
            "HIGH":     "Reduce stimulus load. Activate breathing guide. Monitor closely for escalation.",
            "MODERATE": "Decrease task difficulty. Increase reinforcement frequency. Observe for 30 seconds.",
            "LOW":      "Session stable. Continue current therapeutic protocol.",
        }
        return mapping.get(risk, "Continue monitoring.")
