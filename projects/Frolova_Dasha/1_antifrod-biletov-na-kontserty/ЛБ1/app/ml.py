from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import lightgbm as lgb
import pandas as pd

from app.schemas import OrderEvent


FEATURES = [
    "ticket_count",
    "amount",
    "purchase_attempts_10m",
    "account_age_days",
    "device_accounts_24h",
    "payment_declines_24h",
    "hour",
    "prior_confirmed_orders",
]


@dataclass
class LightGBMAdapter:
    """Adapter pattern: exposes a stable scoring interface over LightGBM."""

    model_path: Path

    def __post_init__(self) -> None:
        self._model = lgb.Booster(model_file=str(self.model_path))

    def predict_risk(self, event: OrderEvent) -> float:
        row = pd.DataFrame([event.ml_features()], columns=FEATURES)
        return round(float(self._model.predict(row)[0]), 4)
