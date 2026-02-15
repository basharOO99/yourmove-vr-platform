"""
Pydantic Schemas for Request/Response Validation
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime


class RotationData(BaseModel):
    """3D rotation data"""
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0


class SensorData(BaseModel):
    """Individual sensor data model"""
    tremor_intensity: float = Field(0.0, ge=0.0)
    stress_trend: float = Field(0.0, ge=0.0)
    stress_timer: float = Field(0.0, ge=0.0)
    rotation: RotationData = Field(default_factory=RotationData)
    delta_rotation: RotationData = Field(default_factory=RotationData)
    average_speed: float = Field(0.0, ge=0.0)


class GlobalMetrics(BaseModel):
    """Global HMD metrics"""
    hmd_eye_dot_product: float = Field(1.0, ge=0.0, le=1.0)


class AllSensors(BaseModel):
    """All 13 body sensors"""
    head: SensorData
    chest: SensorData
    hip: SensorData
    left_hand: SensorData
    right_hand: SensorData
    left_upper_arm: SensorData
    right_upper_arm: SensorData
    left_lower_arm: SensorData
    right_lower_arm: SensorData
    left_upper_leg: SensorData
    right_upper_leg: SensorData
    left_lower_leg: SensorData
    right_lower_leg: SensorData


class VRSensorInput(BaseModel):
    """Input model from Unreal Engine 5"""
    session_id: str
    patient_id: str
    global_metrics: GlobalMetrics
    sensors: AllSensors


class AICommand(BaseModel):
    """AI-generated command response"""
    command: str
    target_sensor: Optional[str] = None
    reason: str
    severity: str


class PatientCreate(BaseModel):
    """Create/Update patient request"""
    name: str
    age: int = Field(gt=0, le=120)
    gender: str
    diagnosis_level: str
    notes: Optional[str] = None


class PatientResponse(BaseModel):
    """Patient response model"""
    id: int
    name: str
    age: int
    gender: str
    diagnosis_level: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DoctorLogin(BaseModel):
    """Login request"""
    username: str
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str
