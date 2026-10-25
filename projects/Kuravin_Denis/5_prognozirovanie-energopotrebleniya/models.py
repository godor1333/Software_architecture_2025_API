import time
import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class AnomalySeverity(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL_PEAK = "CRITICAL_PEAK"

class MeterReadingEvent(BaseModel):
    reading_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    building_id: str = "BLD-MAIN-01"
    timestamp: float = Field(default_factory=time.time)
    meter_reading_kwh: float = Field(..., ge=0.0)
    outside_temp_c: float = 18.5
    humidity_pct: float = 55.0
    building_type: str = "university_campus"
    square_meters: float = 12500.0

class EnergyForecastRequest(BaseModel):
    building_id: str = "BLD-MAIN-01"
    horizon_hours: int = Field(default=6, ge=1, le=48)
    forecast_temp_c: Optional[float] = 20.0
    forecast_humidity: Optional[float] = 50.0

class HourlyForecastPoint(BaseModel):
    hour_offset: int
    predicted_kwh: float
    expected_lower_bound: float
    expected_upper_bound: float

class EnergyForecastResponse(BaseModel):
    building_id: str
    horizon_hours: int
    points: List[HourlyForecastPoint] = []
    predicted_peak_kwh: float
    model_name: str = "XGBoost-Energy-Regressor"
    latency_ms: float = 0.0

class AnomalyAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: f"ALT-{str(uuid.uuid4())[:8]}")
    building_id: str
    timestamp: float = Field(default_factory=time.time)
    actual_kwh: float
    predicted_kwh: float
    residual_kwh: float
    z_score: float
    severity: AnomalySeverity
    reason: str

class BuildingEnergyStats(BaseModel):
    building_id: str
    total_telemetry_points: int
    current_power_kwh: float
    avg_power_kwh: float
    historical_peak_kwh: float
    anomalies_detected: int
    recent_anomalies: List[AnomalyAlert] = []
