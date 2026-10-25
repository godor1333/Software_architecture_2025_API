from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from collections import defaultdict
from ..models import MeterReadingEvent, AnomalyAlert, BuildingEnergyStats

class ITelemetryRepository(ABC):
    """Интерфейс репозитория телеметрии и аномалий энергопотребления (Repository Pattern)."""

    @abstractmethod
    def save_reading(self, event: MeterReadingEvent, alert: Optional[AnomalyAlert] = None) -> None:
        pass

    @abstractmethod
    def get_recent_history(self, building_id: str, limit: int = 24) -> List[float]:
        pass

    @abstractmethod
    def get_building_stats(self, building_id: str) -> BuildingEnergyStats:
        pass

    @abstractmethod
    def list_anomalies(self, limit: int = 50) -> List[AnomalyAlert]:
        pass

class InMemoryTelemetryRepository(ITelemetryRepository):
    """Потокобезопасный In-Memory репозиторий для автономной работы и тестирования."""

    def __init__(self):
        self._readings: Dict[str, List[MeterReadingEvent]] = defaultdict(list)
        self._anomalies: List[AnomalyAlert] = []

    def save_reading(self, event: MeterReadingEvent, alert: Optional[AnomalyAlert] = None) -> None:
        self._readings[event.building_id].append(event)
        if alert is not None and alert.severity != "NORMAL":
            self._anomalies.append(alert)

    def get_recent_history(self, building_id: str, limit: int = 24) -> List[float]:
        items = self._readings.get(building_id, [])
        return [it.meter_reading_kwh for it in items[-limit:]]

    def get_building_stats(self, building_id: str) -> BuildingEnergyStats:
        items = self._readings.get(building_id, [])
        if not items:
            return BuildingEnergyStats(
                building_id=building_id,
                total_telemetry_points=0,
                current_power_kwh=0.0,
                avg_power_kwh=0.0,
                historical_peak_kwh=0.0,
                anomalies_detected=0
            )

        powers = [it.meter_reading_kwh for it in items]
        anomalies_for_bld = [a for a in self._anomalies if a.building_id == building_id]

        return BuildingEnergyStats(
            building_id=building_id,
            total_telemetry_points=len(items),
            current_power_kwh=round(powers[-1], 2),
            avg_power_kwh=round(sum(powers) / len(powers), 2),
            historical_peak_kwh=round(max(powers), 2),
            anomalies_detected=len(anomalies_for_bld),
            recent_anomalies=anomalies_for_bld[-5:]
        )

    def list_anomalies(self, limit: int = 50) -> List[AnomalyAlert]:
        return self._anomalies[-limit:]
