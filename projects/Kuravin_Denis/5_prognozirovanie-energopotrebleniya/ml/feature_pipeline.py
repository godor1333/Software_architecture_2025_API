import math
import numpy as np
from typing import Dict, List, Any

class TimeSeriesFeaturePipeline:
    """Конвейер извлечения признаков для прогнозирования временных рядов энергопотребления."""

    @staticmethod
    def extract_features(
        hour: int,
        day_of_week: int,
        temp_c: float,
        humidity_pct: float,
        lag_1h: float,
        lag_24h: float,
        rolling_mean_6h: float
    ) -> Dict[str, float]:
        # Циклический энкодинг часа суток
        sin_hour = math.sin(2 * math.pi * hour / 24.0)
        cos_hour = math.cos(2 * math.pi * hour / 24.0)

        is_weekend = 1.0 if day_of_week in [5, 6] else 0.0

        # Квадратичный эффект температуры (HVAC нагрузка при морозе и жаре)
        temp_effect = (temp_c - 18.0) ** 2

        return {
            "hour": float(hour),
            "sin_hour": round(sin_hour, 4),
            "cos_hour": round(cos_hour, 4),
            "day_of_week": float(day_of_week),
            "is_weekend": is_weekend,
            "temp_c": float(temp_c),
            "temp_effect": round(temp_effect, 2),
            "humidity_pct": float(humidity_pct),
            "lag_1h": float(lag_1h),
            "lag_24h": float(lag_24h),
            "rolling_mean_6h": float(rolling_mean_6h)
        }

    @staticmethod
    def feature_vector(features: Dict[str, float]) -> List[float]:
        ordered_keys = [
            "hour",
            "sin_hour",
            "cos_hour",
            "day_of_week",
            "is_weekend",
            "temp_c",
            "temp_effect",
            "humidity_pct",
            "lag_1h",
            "lag_24h",
            "rolling_mean_6h"
        ]
        return [features[k] for k in ordered_keys]
