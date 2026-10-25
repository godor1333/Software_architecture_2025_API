import time
import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DamageClass(str, Enum):
    SCRATCH = "scratch"                    # Царапина лакокрасочного покрытия
    DENT = "dent"                          # Вмятина кузовной детали
    BROKEN_HEADLIGHT = "broken_headlight"  # Разбитая / треснутая фара
    CRACKED_GLASS = "cracked_glass"        # Скол / трещина на стекле
    BUMPER_DAMAGE = "bumper_damage"        # Деформация / раскол бампера

class SeverityLevel(str, Enum):
    MINOR = "minor"       # Косметическое (полировка, мелкая подкраска)
    MODERATE = "moderate" # Локальный кузовной ремонт / выпрямление без покраски
    SEVERE = "severe"     # Замена детали / сложный стапельный ремонт

class DamageBoundingBox(BaseModel):
    box_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    damage_type: DamageClass
    confidence: float = Field(..., ge=0.0, le=1.0)
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    severity: SeverityLevel
    estimated_repair_rub: float

class CarDamageReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_vin: Optional[str] = "XTA210900Y1234567"
    client_id: Optional[str] = "client_default"
    raw_image_url: str
    annotated_image_url: str
    damages: List[DamageBoundingBox] = []
    total_damages_count: int = 0
    overall_severity: SeverityLevel = SeverityLevel.MINOR
    total_estimated_repair_rub: float = 0.0
    model_name: str = "YOLOv8-CarDamage-v1"
    processing_time_ms: float = 0.0
    created_at: float = Field(default_factory=time.time)

class InspectionRequest(BaseModel):
    vehicle_vin: Optional[str] = "XTA210900Y1234567"
    client_id: Optional[str] = "insurance_company_1"
    detector_strategy: Optional[str] = "yolov8_fast"
    image_base64: Optional[str] = None

class InspectionSummaryMetrics(BaseModel):
    total_inspections: int
    total_damages_detected: int
    avg_damages_per_car: float
    avg_processing_time_ms: float
    damage_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
