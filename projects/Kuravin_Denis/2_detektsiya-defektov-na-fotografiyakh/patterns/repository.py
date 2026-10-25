from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from collections import defaultdict
from ..models import CarDamageReport, InspectionSummaryMetrics

class IDamageReportRepository(ABC):
    """Интерфейс репозитория отчетов об ущербе (Repository Pattern)."""

    @abstractmethod
    def save_report(self, report: CarDamageReport) -> None:
        pass

    @abstractmethod
    def get_by_id(self, report_id: str) -> Optional[CarDamageReport]:
        pass

    @abstractmethod
    def list_reports(self, limit: int = 50) -> List[CarDamageReport]:
        pass

    @abstractmethod
    def get_summary_metrics(self) -> InspectionSummaryMetrics:
        pass

class InMemoryReportRepository(IDamageReportRepository):
    """Потокобезопасная In-Memory реализация для автономной работы и тестов."""

    def __init__(self):
        self._storage: Dict[str, CarDamageReport] = {}
        self._total_latency_ms: float = 0.0

    def save_report(self, report: CarDamageReport) -> None:
        self._storage[report.report_id] = report
        self._total_latency_ms += report.processing_time_ms

    def get_by_id(self, report_id: str) -> Optional[CarDamageReport]:
        return self._storage.get(report_id)

    def list_reports(self, limit: int = 50) -> List[CarDamageReport]:
        return list(self._storage.values())[-limit:]

    def get_summary_metrics(self) -> InspectionSummaryMetrics:
        reports = list(self._storage.values())
        total_reports = len(reports)
        total_damages = sum(r.total_damages_count for r in reports)
        avg_damages = (total_damages / total_reports) if total_reports > 0 else 0.0
        avg_latency = (self._total_latency_ms / total_reports) if total_reports > 0 else 0.0

        damage_dist = defaultdict(int)
        severity_dist = defaultdict(int)

        for r in reports:
            severity_dist[r.overall_severity.value] += 1
            for d in r.damages:
                damage_dist[d.damage_type.value] += 1

        return InspectionSummaryMetrics(
            total_inspections=total_reports,
            total_damages_detected=total_damages,
            avg_damages_per_car=round(avg_damages, 2),
            avg_processing_time_ms=round(avg_latency, 2),
            damage_distribution=dict(damage_dist),
            severity_distribution=dict(severity_dist)
        )
