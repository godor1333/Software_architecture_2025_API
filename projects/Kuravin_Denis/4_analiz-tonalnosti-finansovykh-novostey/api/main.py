from typing import List
from fastapi import FastAPI, HTTPException, Query
from ..models import (
    NewsItem,
    NewsAnalysisResult,
    CompanySentimentAggregate,
    NewsBatchRequest,
    NewsBatchResponse
)
from ..config import settings
from ..nlp.ner_extractor import FinancialNERExtractor
from ..patterns.strategy import FinBERTStrategy, LexiconStrategy
from ..patterns.observer import MarketSentimentSubject, RiskAlertObserver, AnalyticsLoggerObserver
from ..patterns.adapter import LocalElasticsearchAdapter, LocalClickHouseAdapter
from ..patterns.repository import InMemoryNewsRepository
from ..patterns.pipeline import NewsAnalysisPipeline

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Потоковый анализ тональности финансовых новостей, извлечение сущностей (NER) и агрегация по компаниям"
)

# Синглтоны компонентов
ner_extractor = FinancialNERExtractor()
default_strategy = FinBERTStrategy()
subject = MarketSentimentSubject()
risk_observer = RiskAlertObserver(negative_threshold=-0.40)
analytics_observer = AnalyticsLoggerObserver()
subject.attach(risk_observer)
subject.attach(analytics_observer)

es_adapter = LocalElasticsearchAdapter()
clickhouse_adapter = LocalClickHouseAdapter()
repository = InMemoryNewsRepository()

pipeline = NewsAnalysisPipeline(
    strategy=default_strategy,
    ner_extractor=ner_extractor,
    subject=subject,
    repository=repository,
    es_adapter=es_adapter,
    clickhouse_adapter=clickhouse_adapter
)

@app.post("/api/v1/news/analyze", response_model=NewsAnalysisResult, tags=["Analysis"])
def analyze_single_news(item: NewsItem):
    """Анализ одиночной финансовой публикации: извлечение тикеров и скоринг тональности."""
    try:
        return pipeline.execute(item)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки новости: {str(e)}")

@app.post("/api/v1/news/batch", response_model=NewsBatchResponse, tags=["Analysis"])
def analyze_news_batch(batch: NewsBatchRequest):
    """Пакетная обработка новостного потока (Kafka Consumer Batch)."""
    results: List[NewsAnalysisResult] = []
    pos, neg, neu = 0, 0, 0

    for item in batch.items:
        res = pipeline.execute(item)
        results.append(res)
        if res.overall_sentiment == "POSITIVE":
            pos += 1
        elif res.overall_sentiment == "NEGATIVE":
            neg += 1
        else:
            neu += 1

    return NewsBatchResponse(
        total_processed=len(results),
        positive_count=pos,
        negative_count=neg,
        neutral_count=neu,
        results=results
    )

@app.get("/api/v1/sentiment/company/{ticker}", response_model=CompanySentimentAggregate, tags=["Market Analytics"])
def get_company_sentiment(ticker: str):
    """Сводный сентимент-индекс по конкретному тикеру (SBER, GAZP, YDEX, T, LKOH, NVDA)."""
    agg = repository.get_company_sentiment(ticker.upper())
    if not agg or agg.total_news_count == 0:
        raise HTTPException(status_code=404, detail=f"По тикеру {ticker.upper()} не найдено новостей.")
    return agg

@app.get("/api/v1/sentiment/overview", response_model=List[CompanySentimentAggregate], tags=["Market Analytics"])
def get_market_overview():
    """Тепловая карта рынка (Market Sentiment Heatmap) по всем компаниям."""
    return repository.get_all_companies_sentiment()

@app.get("/api/v1/alerts", tags=["Risk Management"])
def get_risk_alerts():
    """Список срочных алертов по компаниям с критическим негативным сентиментом."""
    return risk_observer.triggered_alerts

@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Проверка состояния сервиса и подключенных брокеров/адаптеров."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "strategy": default_strategy.name,
        "environment": settings.environment
    }
