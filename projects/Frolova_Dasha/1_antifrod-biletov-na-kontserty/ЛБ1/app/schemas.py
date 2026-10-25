from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Decision(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"


class OrderEvent(BaseModel):
    order_id: str = Field(min_length=3, max_length=64)
    account_id: str = Field(min_length=3, max_length=64)
    device_id: str = Field(min_length=3, max_length=64)
    event_id: str = Field(min_length=3, max_length=64)
    ticket_count: int = Field(ge=1, le=20)
    amount: float = Field(gt=0, le=500_000)
    purchase_attempts_10m: int = Field(ge=1, le=100)
    account_age_days: int = Field(ge=0, le=36_500)
    device_accounts_24h: int = Field(ge=1, le=100)
    payment_declines_24h: int = Field(default=0, ge=0, le=50)
    hour: int = Field(default=12, ge=0, le=23)
    prior_confirmed_orders: int = Field(default=0, ge=0, le=1_000)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("occurred_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def ml_features(self) -> dict[str, float | int]:
        return {
            "ticket_count": self.ticket_count,
            "amount": self.amount,
            "purchase_attempts_10m": self.purchase_attempts_10m,
            "account_age_days": self.account_age_days,
            "device_accounts_24h": self.device_accounts_24h,
            "payment_declines_24h": self.payment_declines_24h,
            "hour": self.hour,
            "prior_confirmed_orders": self.prior_confirmed_orders,
        }


class RuleHit(BaseModel):
    code: str
    description: str
    weight: float


class ScoreResponse(BaseModel):
    order_id: str
    risk_score: float = Field(ge=0, le=1)
    decision: Decision
    reasons: list[RuleHit]
    model_version: str
    scored_at: datetime


class OrderSubmission(BaseModel):
    """Asynchronous acknowledgement returned when the Kafka pipeline is enabled."""

    order_id: str
    status: str = "PENDING"
    message: str


class DashboardSummary(BaseModel):
    total_events: int
    review_events: int
    review_rate: float
    average_risk_score: float
    model_version: str
