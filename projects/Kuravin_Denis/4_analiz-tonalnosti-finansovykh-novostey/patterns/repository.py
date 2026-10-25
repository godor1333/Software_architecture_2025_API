from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from collections import defaultdict
from ..models import (
    NewsItem,
    NewsAnalysisResult,
    CompanySentimentAggregate,
    MarketTrend,
    SentimentLabel
)

class INewsRepository(ABC):
    """Интерфейс репозитория новостей и агрегатов сентимента (Repository Pattern)."""

    @abstractmethod
    def save_analysis(self, item: NewsItem, result: NewsAnalysisResult) -> None:
        pass

    @abstractmethod
    def get_by_id(self, news_id: str) -> Optional[NewsAnalysisResult]:
        pass

    @abstractmethod
    def list_recent(self, limit: int = 50) -> List[NewsAnalysisResult]:
        pass

    @abstractmethod
    def get_company_sentiment(self, ticker: str) -> CompanySentimentAggregate:
        pass

    @abstractmethod
    def get_all_companies_sentiment(self) -> List[CompanySentimentAggregate]:
        pass

class InMemoryNewsRepository(INewsRepository):
    """Потокобезопасная In-Memory реализация репозитория для автономной работы и тестирования."""

    def __init__(self):
        self._items: Dict[str, NewsItem] = {}
        self._results: Dict[str, NewsAnalysisResult] = {}
        self._ticker_results: Dict[str, List[NewsAnalysisResult]] = defaultdict(list)
        self._ticker_names: Dict[str, str] = {
            "SBER": "ПАО Сбербанк",
            "GAZP": "ПАО Газпром",
            "YDEX": "Яндекс",
            "T": "Т-Банк",
            "LKOH": "ПАО Лукойл",
            "NVDA": "Nvidia Corporation",
            "AAPL": "Apple Inc."
        }

    def save_analysis(self, item: NewsItem, result: NewsAnalysisResult) -> None:
        self._items[item.news_id] = item
        self._results[result.news_id] = result

        for ent in result.entities:
            self._ticker_results[ent.ticker].append(result)
            if ent.ticker not in self._ticker_names:
                self._ticker_names[ent.ticker] = ent.name

    def get_by_id(self, news_id: str) -> Optional[NewsAnalysisResult]:
        return self._results.get(news_id)

    def list_recent(self, limit: int = 50) -> List[NewsAnalysisResult]:
        return list(self._results.values())[-limit:]

    def get_company_sentiment(self, ticker: str) -> CompanySentimentAggregate:
        results = self._ticker_results.get(ticker, [])
        company_name = self._ticker_names.get(ticker, ticker)

        if not results:
            return CompanySentimentAggregate(
                ticker=ticker,
                company_name=company_name,
                total_news_count=0,
                sentiment_index=0.0,
                market_trend=MarketTrend.NEUTRAL
            )

        pos = sum(1 for r in results if r.overall_sentiment == SentimentLabel.POSITIVE)
        neg = sum(1 for r in results if r.overall_sentiment == SentimentLabel.NEGATIVE)
        neu = sum(1 for r in results if r.overall_sentiment == SentimentLabel.NEUTRAL)
        avg_score = sum(r.sentiment_score for r in results) / len(results)

        if avg_score >= 0.20:
            trend = MarketTrend.BULLISH
        elif avg_score <= -0.20:
            trend = MarketTrend.BEARISH
        else:
            trend = MarketTrend.NEUTRAL

        return CompanySentimentAggregate(
            ticker=ticker,
            company_name=company_name,
            total_news_count=len(results),
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            sentiment_index=round(avg_score, 3),
            market_trend=trend,
            recent_news=results[-5:]
        )

    def get_all_companies_sentiment(self) -> List[CompanySentimentAggregate]:
        tickers = list(self._ticker_names.keys())
        return [self.get_company_sentiment(t) for t in tickers if t in self._ticker_results]
