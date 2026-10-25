import os
import joblib
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from ..models import HourlyForecastPoint
from ..ml.feature_pipeline import TimeSeriesFeaturePipeline

class IForecastingStrategy(ABC):
    """Интерфейс стратегии прогнозирования энергопотребления (Strategy Pattern)."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def forecast_next_hours(
        self,
        current_kwh: float,
        start_hour: int,
        day_of_week: int,
        temp_c: float,
        humidity_pct: float,
        horizon_hours: int = 6,
        history_24h: List[float] = None
    ) -> Tuple[List[HourlyForecastPoint], float]:
        pass

class XGBoostForecastingStrategy(IForecastingStrategy):
    """Стратегия прогнозирования на основе обученной модели градиентного бустинга XGBoost."""

    def __init__(self):
        self._name = "XGBoost-Energy-Regressor"
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(current_dir, "ml", "model.joblib")
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            self.model = None

    @property
    def name(self) -> str:
        return self._name

    def forecast_next_hours(
        self,
        current_kwh: float,
        start_hour: int,
        day_of_week: int,
        temp_c: float,
        humidity_pct: float,
        horizon_hours: int = 6,
        history_24h: List[float] = None
    ) -> Tuple[List[HourlyForecastPoint], float]:
        points: List[HourlyForecastPoint] = []
        rolling_buffer = list(history_24h) if history_24h else [current_kwh] * 24
        sim_current = current_kwh

        for offset in range(1, horizon_hours + 1):
            h = (start_hour + offset) % 24
            dow = (day_of_week + ((start_hour + offset) // 24)) % 7

            lag_1 = sim_current
            lag_24 = rolling_buffer[-(24 - offset)] if len(rolling_buffer) >= 24 else sim_current
            roll_6 = sum(rolling_buffer[-6:]) / min(6, len(rolling_buffer))

            feats = TimeSeriesFeaturePipeline.extract_features(
                hour=h,
                day_of_week=dow,
                temp_c=temp_c,
                humidity_pct=humidity_pct,
                lag_1h=lag_1,
                lag_24h=lag_24,
                rolling_mean_6h=roll_6
            )
            vec = TimeSeriesFeaturePipeline.feature_vector(feats)

            if self.model is not None:
                pred = float(self.model.predict([vec])[0])
            else:
                pred = roll_6 * 1.05

            pred = max(100.0, pred)
            rolling_buffer.append(pred)
            sim_current = pred

            # 95% доверительный интервал (~2 * RMSE = 26.5 кВт)
            lower = max(0.0, pred - 26.5)
            upper = pred + 26.5

            points.append(HourlyForecastPoint(
                hour_offset=offset,
                predicted_kwh=round(pred, 2),
                expected_lower_bound=round(lower, 2),
                expected_upper_bound=round(upper, 2)
            ))

        peak = max(p.predicted_kwh for p in points) if points else current_kwh
        return points, round(peak, 2)

class BaselinePersistenceStrategy(IForecastingStrategy):
    """Наивная стратегия постоянства (прогноз равен потреблению 24 часа назад)."""

    @property
    def name(self) -> str:
        return "Naive-Persistence-24h"

    def forecast_next_hours(
        self,
        current_kwh: float,
        start_hour: int,
        day_of_week: int,
        temp_c: float,
        humidity_pct: float,
        horizon_hours: int = 6,
        history_24h: List[float] = None
    ) -> Tuple[List[HourlyForecastPoint], float]:
        points = []
        for offset in range(1, horizon_hours + 1):
            pred = current_kwh
            points.append(HourlyForecastPoint(
                hour_offset=offset,
                predicted_kwh=round(pred, 2),
                expected_lower_bound=round(pred * 0.85, 2),
                expected_upper_bound=round(pred * 1.15, 2)
            ))
        return points, current_kwh
