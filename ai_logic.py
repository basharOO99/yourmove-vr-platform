"""
AI Movement Analysis Logic for YourMove VR Therapy System
Processes high-frequency sensor data and generates adaptive commands
"""
from typing import Dict, List, Tuple
from schemas import VRSensorInput, AICommand, SensorData
import time


class MovementAnalyzer:
    """Real-time AI analyzer for VR sensor data"""
    
    # Thresholds for detection
    STRESS_TREND_THRESHOLD = 15.0
    STRESS_TIMER_THRESHOLD = 3.0
    TREMOR_INTENSITY_THRESHOLD = 5.0
    FOCUS_THRESHOLD = 0.6
    
    # Body part display names
    BODY_PART_NAMES = {
        "head": "Head",
        "chest": "Chest",
        "hip": "Hip",
        "left_hand": "Left Hand",
        "right_hand": "Right Hand",
        "left_upper_arm": "Left Upper Arm",
        "right_upper_arm": "Right Upper Arm",
        "left_lower_arm": "Left Lower Arm",
        "right_lower_arm": "Right Lower Arm",
        "left_upper_leg": "Left Upper Leg",
        "right_upper_leg": "Right Upper Leg",
        "left_lower_leg": "Left Lower Leg",
        "right_lower_leg": "Right Lower Leg",
    }
    
    def __init__(self):
        self.session_start_time = time.time()
        self.event_history = []
    
    def analyze_movement(self, data: VRSensorInput) -> AICommand:
        """
        Main analysis function - processes all sensor data and returns AI command
        
        Detection Logic:
        1. High Stress Detection: stress_trend > 15 AND stress_timer > 3.0
        2. Severe Tremor Detection: tremor_intensity > 5.0
        3. Focus Loss Detection: hmd_eye_dot_product < 0.6
        """
        
        # Check focus first (global metric)
        if data.global_metrics.hmd_eye_dot_product < self.FOCUS_THRESHOLD:
            return AICommand(
                command="refocus",
                target_sensor="hmd",
                reason=f"Patient distracted - Eye tracking shows {data.global_metrics.hmd_eye_dot_product:.2f} focus level",
                severity="medium"
            )
        
        # Analyze all body sensors for stress and tremors
        critical_sensors = []
        high_stress_sensors = []
        tremor_sensors = []
        
        sensors_dict = data.sensors.dict()
        
        for sensor_name, sensor_data in sensors_dict.items():
            # Check for high stress (potential outburst)
            if (sensor_data['stress_trend'] > self.STRESS_TREND_THRESHOLD and 
                sensor_data['stress_timer'] > self.STRESS_TIMER_THRESHOLD):
                critical_sensors.append((sensor_name, sensor_data))
            
            # Check for elevated stress
            elif sensor_data['stress_trend'] > 10.0:
                high_stress_sensors.append((sensor_name, sensor_data))
            
            # Check for tremors
            if sensor_data['tremor_intensity'] > self.TREMOR_INTENSITY_THRESHOLD:
                tremor_sensors.append((sensor_name, sensor_data))
        
        # Prioritize critical stress (imminent outburst)
        if critical_sensors:
            sensor_name, sensor_data = critical_sensors[0]
            return AICommand(
                command="calm_down",
                target_sensor=sensor_name,
                reason=f"Critical stress detected in {self.BODY_PART_NAMES[sensor_name]} - Trend: {sensor_data['stress_trend']:.1f}, Duration: {sensor_data['stress_timer']:.1f}s",
                severity="critical"
            )
        
        # Handle severe tremors
        if tremor_sensors:
            sensor_name, sensor_data = tremor_sensors[0]
            return AICommand(
                command="pause_and_breathe",
                target_sensor=sensor_name,
                reason=f"Severe tremor in {self.BODY_PART_NAMES[sensor_name]} - Intensity: {sensor_data['tremor_intensity']:.1f}",
                severity="high"
            )
        
        # Handle elevated stress (preventive)
        if high_stress_sensors:
            sensor_name, sensor_data = high_stress_sensors[0]
            return AICommand(
                command="slow_down",
                target_sensor=sensor_name,
                reason=f"Elevated stress in {self.BODY_PART_NAMES[sensor_name]} - Trend: {sensor_data['stress_trend']:.1f}",
                severity="medium"
            )
        
        # All clear - encourage patient
        return AICommand(
            command="continue",
            target_sensor=None,
            reason="All metrics stable - Patient performing well",
            severity="low"
        )
    
    def get_body_part_status(self, data: VRSensorInput) -> Dict[str, dict]:
        """
        Generate status for each body part for dashboard visualization
        Returns dict with color coding and metrics
        """
        status = {}
        sensors_dict = data.sensors.dict()
        
        for sensor_name, sensor_data in sensors_dict.items():
            # Determine status color
            if (sensor_data['stress_trend'] > self.STRESS_TREND_THRESHOLD and 
                sensor_data['stress_timer'] > self.STRESS_TIMER_THRESHOLD):
                color = "critical"  # Red
            elif sensor_data['tremor_intensity'] > self.TREMOR_INTENSITY_THRESHOLD:
                color = "warning"  # Orange
            elif sensor_data['stress_trend'] > 10.0:
                color = "elevated"  # Yellow
            else:
                color = "normal"  # Green
            
            status[sensor_name] = {
                "name": self.BODY_PART_NAMES[sensor_name],
                "color": color,
                "tremor": round(sensor_data['tremor_intensity'], 2),
                "stress_trend": round(sensor_data['stress_trend'], 2),
                "stress_timer": round(sensor_data['stress_timer'], 2),
                "speed": round(sensor_data['average_speed'], 2)
            }
        
        return status
    
    def get_global_stats(self, data: VRSensorInput) -> Dict[str, float]:
        """Calculate global statistics across all sensors"""
        sensors_dict = data.sensors.dict()
        
        tremor_values = [s['tremor_intensity'] for s in sensors_dict.values()]
        stress_values = [s['stress_trend'] for s in sensors_dict.values()]
        
        return {
            "max_tremor": round(max(tremor_values), 2),
            "avg_tremor": round(sum(tremor_values) / len(tremor_values), 2),
            "max_stress": round(max(stress_values), 2),
            "avg_stress": round(sum(stress_values) / len(stress_values), 2),
            "focus_level": round(data.global_metrics.hmd_eye_dot_product, 2)
        }
