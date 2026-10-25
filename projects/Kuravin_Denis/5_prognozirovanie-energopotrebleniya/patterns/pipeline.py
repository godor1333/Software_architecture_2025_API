import time
from datetime import datetime
from typing import Tuple, Optional
from ..models import MeterReadingEvent, AnomalyAlert, AnomalySeverity
from .strategy import IForecastingStrategy
from .observer import EnergyAlertSubject
from .repository import ITelemetryRepository
from ..ml.anomaly_detector import EnergyAnomalyDetector

class EnergyTelemetryPipeline:
    """Конвейер обработки IoT-телеметрии, прогнозирования и выявления аномалий (Pipeline Pattern)."""

    def __init__(
        self,
        strategy: IForecastingStrategy,
        subject: EnergyAlertSubject,
        repository: ITelemetryRepository,
        anomaly_detector: EnergyAnomalyDetector
    ):
        self.strategy = strategy
        self.subject = subject
        self.repository = repository
        self.detector = anomaly_detector

    def stage_1_validate(self, event: MeterReadingEvent) -> None:
        if event.meter_reading_kwh < 0.0:
            raise ValueError("Показания счетчика не могут быть отрицательными.")

    def stage_2_forecast_expected(self, event: MeterReadingEvent) -> float:
        dt = datetime.fromtimestamp(event.timestamp)
        h = dt.hour
        dow = dt.weekday()
        history_24 = self.repository.get_recent_history(event.building_id, limit=24)
        current = history_24[-1] if history_24 else event.meter_reading_kwh

        points, _ = self.strategy.forecast_next_hours(
            current_kwh=current,
            start_hour=h,
            day_of_week=dow,
            temp_c=event.outside_temp_c,
            humidity_pct=event.humidity_pct,
            horizon_hours=1,
            history_24h=history_24
        )
        return points[0].predicted_kwh if points else event.meter_reading_kwh

    def stage_3_detect_anomalies(
        self,
        event: MeterReadingEvent,
        predicted_kwh: float
    ) -> AnomalyAlert:
        sev, res, z, reason = self.detector.evaluate(
            building_id=event.building_id,
            actual_kwh=event.meter_reading_kwh,
            predicted_kwh=predicted_kwh,
            timestamp=event.timestamp
        )

        return AnomalyAlert(
            building_id=event.building_id,
            timestamp=event.timestamp,
            actual_kwh=round(event.meter_reading_kwh, 2),
            predicted_kwh=round(predicted_kwh, 2),
            residual_kwh=res,
            z_score=z,
            severity=sev,
            reason=reason
        )

    def stage_4_notify_and_persist(self, event: MeterReadingEvent, alert: AnomalyAlert) -> None:
        self.repository.save_reading(event, alert)
        if alert.severity != AnomalySeverity.NORMAL:
            self.subject.notify(alert)

    def execute(self, event: MeterReadingEvent) -> AnomalyAlert:
        self.stage_1_validate(event)
        expected_kwh = self.stage_2_forecast_expected(event)
        alert = self.stage_3_detect_anomalies(event, expected_kwh)
        self.stage_4_notify_and_persist(event, alert)
        return alert
