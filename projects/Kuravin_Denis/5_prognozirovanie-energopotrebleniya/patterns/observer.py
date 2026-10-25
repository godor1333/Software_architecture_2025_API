from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..models import AnomalyAlert, AnomalySeverity

class IEnergyAlertObserver(ABC):
    """Интерфейс наблюдателя за аномалиями энергопотребления (Observer Pattern)."""

    @abstractmethod
    def on_anomaly(self, alert: AnomalyAlert) -> None:
        pass

class OverloadDispatchObserver(IEnergyAlertObserver):
    """Диспетчерский наблюдатель: оповещает службу главного энергетика при аварийных пиках."""

    def __init__(self):
        self.dispatched_alerts: List[AnomalyAlert] = []

    def on_anomaly(self, alert: AnomalyAlert) -> None:
        if alert.severity in [AnomalySeverity.WARNING, AnomalySeverity.CRITICAL_PEAK]:
            self.dispatched_alerts.append(alert)
            print(f"[DISPATCH ALERT] {alert.severity.value}: {alert.building_id} -> {alert.reason} (Fact: {alert.actual_kwh} kW)")

class FacilityDashboardObserver(IEnergyAlertObserver):
    """Наблюдатель для обновления счетчиков на диспетчерском экране Grafana."""

    def __init__(self):
        self.events_count = 0

    def on_anomaly(self, alert: AnomalyAlert) -> None:
        self.events_count += 1

class EnergyAlertSubject:
    """Субъект (издатель) оповещений об энергоаномалиях."""

    def __init__(self):
        self._observers: List[IEnergyAlertObserver] = []

    def attach(self, observer: IEnergyAlertObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: IEnergyAlertObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, alert: AnomalyAlert) -> None:
        for obs in self._observers:
            obs.on_anomaly(alert)
