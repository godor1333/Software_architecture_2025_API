from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models import NewsAnalysisResult

class IElasticsearchAdapter(ABC):
    """Интерфейс адаптера к полнотекстовому поисковому движку Elasticsearch (Adapter Pattern)."""

    @abstractmethod
    def index_news(self, result: NewsAnalysisResult, content: str) -> bool:
        pass

    @abstractmethod
    def search_news(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        pass

class LocalElasticsearchAdapter(IElasticsearchAdapter):
    """Локальный адаптер Elasticsearch для автономного запуска и тестов."""

    def __init__(self):
        self._documents: Dict[str, Dict[str, Any]] = {}

    def index_news(self, result: NewsAnalysisResult, content: str) -> bool:
        self._documents[result.news_id] = {
            "news_id": result.news_id,
            "title": result.title,
            "content": content,
            "sentiment": result.overall_sentiment.value,
            "score": result.sentiment_score,
            "tickers": [e.ticker for e in result.entities]
        }
        return True

    def search_news(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = query.lower()
        matched = []
        for doc in self._documents.values():
            if q in doc["title"].lower() or q in doc["content"].lower():
                matched.append(doc)
        return matched[:limit]

class IClickHouseAdapter(ABC):
    """Интерфейс адаптера к аналитической СУБД ClickHouse."""

    @abstractmethod
    def record_sentiment_point(self, ticker: str, score: float, timestamp: float) -> None:
        pass

class LocalClickHouseAdapter(IClickHouseAdapter):
    """Локальный адаптер аналитики ClickHouse."""

    def __init__(self):
        self._points: List[Dict[str, Any]] = []

    def record_sentiment_point(self, ticker: str, score: float, timestamp: float) -> None:
        self._points.append({
            "ticker": ticker,
            "score": score,
            "timestamp": timestamp
        })
