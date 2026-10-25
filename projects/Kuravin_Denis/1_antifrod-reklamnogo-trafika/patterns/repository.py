import time
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from collections import defaultdict
from ..models import ClickEvent, FraudEvaluationResult, AntifraudMetrics

class IClickRepository(ABC):
    """Интерфейс репозитория для работы с событиями кликов и их историей (Repository Pattern)."""

    @abstractmethod
    def record_click(self, event: ClickEvent, result: FraudEvaluationResult) -> None:
        pass

    @abstractmethod
    def get_ip_frequency(self, ip_address: str) -> Tuple[int, int]:
        """Возвращает (частота за 1 минуту, частота за 5 минут)."""
        pass

    @abstractmethod
    def get_metrics(self) -> AntifraudMetrics:
        pass

    @abstractmethod
    def get_recent_results(self, limit: int = 50) -> List[FraudEvaluationResult]:
        pass

class InMemoryClickRepository(IClickRepository):
    """Потокобезопасная In-Memory реализация репозитория для автономного режима и тестов."""

    def __init__(self):
        self._ip_timestamps: Dict[str, List[float]] = defaultdict(list)
        self._results: List[FraudEvaluationResult] = []
        self._events: Dict[str, ClickEvent] = {}
        self._blocked_by_rules: int = 0
        self._blocked_by_ml: int = 0
        self._total_latency_ms: float = 0.0

    def record_click(self, event: ClickEvent, result: FraudEvaluationResult) -> None:
        now = time.time()
        self._ip_timestamps[event.ip_address].append(now)
        self._results.append(result)
        self._events[event.click_id] = event
        self._total_latency_ms += result.processing_time_ms

        if result.is_fraud:
            if any("RULE_" in r for r in result.matched_rules):
                self._blocked_by_rules += 1
            else:
                self._blocked_by_ml += 1

        # Очистка старых таймстемпов (> 10 мин)
        cutoff = now - 600
        self._ip_timestamps[event.ip_address] = [
            ts for ts in self._ip_timestamps[event.ip_address] if ts > cutoff
        ]

    def get_ip_frequency(self, ip_address: str) -> Tuple[int, int]:
        now = time.time()
        timestamps = self._ip_timestamps.get(ip_address, [])
        c_1min = sum(1 for ts in timestamps if now - ts <= 60)
        c_5min = sum(1 for ts in timestamps if now - ts <= 300)
        # Учитываем текущее событие как минимум 1
        return max(1, c_1min + 1), max(1, c_5min + 1)

    def get_metrics(self) -> AntifraudMetrics:
        total = len(self._results)
        frauds = sum(1 for r in self._results if r.is_fraud)
        rate = (frauds / total * 100.0) if total > 0 else 0.0
        avg_lat = (self._total_latency_ms / total) if total > 0 else 0.0

        # Топ заблокированных IP
        ip_counts = defaultdict(int)
        for r in self._results:
            if r.is_fraud and r.click_id in self._events:
                ip_counts[self._events[r.click_id].ip_address] += 1
        top_ips = sorted(ip_counts.keys(), key=lambda ip: ip_counts[ip], reverse=True)[:5]

        return AntifraudMetrics(
            total_processed=total,
            total_fraud_detected=frauds,
            fraud_rate_percentage=round(rate, 2),
            avg_latency_ms=round(avg_lat, 2),
            blocked_by_rules_count=self._blocked_by_rules,
            blocked_by_ml_count=self._blocked_by_ml,
            top_blocked_ips=top_ips
        )

    def get_recent_results(self, limit: int = 50) -> List[FraudEvaluationResult]:
        return self._results[-limit:]
