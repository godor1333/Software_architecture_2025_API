import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..models import NewsAnalysisResult, SentimentLabel

class INewsSentimentObserver(ABC):
    """Интерфейс наблюдателя за изменениями финансового сентимента (Observer Pattern)."""

    @abstractmethod
    def update(self, result: NewsAnalysisResult) -> None:
        pass

class RiskAlertObserver(INewsSentimentObserver):
    """Наблюдатель для генерации срочных алертов риск-менеджерам и трейдерам при резком негативе."""

    def __init__(self, negative_threshold: float = -0.40):
        self.negative_threshold = negative_threshold
        self.triggered_alerts: List[Dict[str, Any]] = []

    def update(self, result: NewsAnalysisResult) -> None:
        if result.sentiment_score <= self.negative_threshold and result.entities:
            tickers = [e.ticker for e in result.entities]
            alert = {
                "alert_id": f"ALT-{int(time.time()*1000)}",
                "news_id": result.news_id,
                "tickers": tickers,
                "sentiment_score": result.sentiment_score,
                "title": result.title,
                "drivers": result.key_drivers,
                "timestamp": time.time()
            }
            self.triggered_alerts.append(alert)
            print(f"[RISK ALERT] Обнаружен сильный негатив по тикерам {tickers}: {result.title} (Score: {result.sentiment_score})")

class AnalyticsLoggerObserver(INewsSentimentObserver):
    """Наблюдатель для сбора логов и отправки метрик в ClickHouse/Grafana."""

    def __init__(self):
        self.processed_count = 0

    def update(self, result: NewsAnalysisResult) -> None:
        self.processed_count += 1

class MarketSentimentSubject:
    """Субъект (издатель), управляющий списком наблюдателей."""

    def __init__(self):
        self._observers: List[INewsSentimentObserver] = []

    def attach(self, observer: INewsSentimentObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: INewsSentimentObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, result: NewsAnalysisResult) -> None:
        for obs in self._observers:
            obs.update(result)
