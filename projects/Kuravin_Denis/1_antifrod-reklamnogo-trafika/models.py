import time
import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FraudStatus(str, Enum):
    ALLOWED = "ALLOWED"
    SUSPICIOUS = "SUSPICIOUS"
    BLOCKED = "BLOCKED"

class ClickEvent(BaseModel):
    click_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    publisher_id: str
    campaign_id: str
    user_id: str
    ip_address: str
    user_agent: str
    timestamp: float = Field(default_factory=time.time)
    url: str
    referer: Optional[str] = None
    device_type: str = "desktop"  # desktop, mobile, tablet, bot_crawler
    os: str = "Windows"
    geo_country: str = "RU"
    click_interval_ms: Optional[int] = 500  # время от показа баннера до клика

class FraudEvaluationResult(BaseModel):
    click_id: str
    is_fraud: bool
    fraud_score: float = Field(..., ge=0.0, le=1.0)
    status: FraudStatus
    primary_reason: str
    matched_rules: List[str] = []
    features_used: Dict[str, float] = {}
    evaluated_at: float = Field(default_factory=time.time)
    processing_time_ms: float = 0.0

class BatchClickRequest(BaseModel):
    events: List[ClickEvent]

class BatchClickResponse(BaseModel):
    total: int
    allowed_count: int
    suspicious_count: int
    blocked_count: int
    results: List[FraudEvaluationResult]

class AntifraudMetrics(BaseModel):
    total_processed: int
    total_fraud_detected: int
    fraud_rate_percentage: float
    avg_latency_ms: float
    blocked_by_rules_count: int
    blocked_by_ml_count: int
    top_blocked_ips: List[str] = []
