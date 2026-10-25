import time
from typing import List
from ..models import NewsItem, NewsAnalysisResult
from ..nlp.ner_extractor import FinancialNERExtractor
from .strategy import ISentimentStrategy
from .observer import MarketSentimentSubject
from .adapter import IElasticsearchAdapter, IClickHouseAdapter
from .repository import INewsRepository

class NewsAnalysisPipeline:
    """Пайплайн анализа финансовых новостей (Pipeline Pattern)."""

    def __init__(
        self,
        strategy: ISentimentStrategy,
        ner_extractor: FinancialNERExtractor,
        subject: MarketSentimentSubject,
        repository: INewsRepository,
        es_adapter: IElasticsearchAdapter,
        clickhouse_adapter: IClickHouseAdapter
    ):
        self.strategy = strategy
        self.ner_extractor = ner_extractor
        self.subject = subject
        self.repository = repository
        self.es_adapter = es_adapter
        self.clickhouse_adapter = clickhouse_adapter

    def stage_1_clean_and_validate(self, item: NewsItem) -> str:
        if not item.title.strip() and not item.content.strip():
            raise ValueError("Новость не содержит текста.")
        # Объединяем заголовок и тело для анализа
        full_text = f"{item.title}. {item.content}".strip()
        return full_text

    def stage_2_ner(self, full_text: str):
        return self.ner_extractor.extract_entities(full_text)

    def stage_3_sentiment(self, full_text: str):
        return self.strategy.evaluate(full_text)

    def stage_4_build_result(self, item: NewsItem, entities, sentiment_data, start_time: float) -> NewsAnalysisResult:
        label, score, conf, drivers = sentiment_data
        elapsed_ms = (time.time() - start_time) * 1000.0

        return NewsAnalysisResult(
            news_id=item.news_id,
            title=item.title,
            overall_sentiment=label,
            sentiment_score=score,
            confidence=conf,
            entities=entities,
            key_drivers=drivers,
            processing_time_ms=round(elapsed_ms, 2)
        )

    def stage_5_notify_and_persist(self, item: NewsItem, result: NewsAnalysisResult) -> None:
        # Сохранение в репозиторий
        self.repository.save_analysis(item, result)

        # Сохранение в адаптеры (ES / ClickHouse)
        self.es_adapter.index_news(result, item.content)
        for ent in result.entities:
            self.clickhouse_adapter.record_sentiment_point(ent.ticker, result.sentiment_score, result.processed_at)

        # Оповещение наблюдателей (Observer)
        self.subject.notify(result)

    def execute(self, item: NewsItem) -> NewsAnalysisResult:
        start_time = time.time()
        text = self.stage_1_clean_and_validate(item)
        entities = self.stage_2_ner(text)
        sentiment_data = self.stage_3_sentiment(text)
        result = self.stage_4_build_result(item, entities, sentiment_data, start_time)
        self.stage_5_notify_and_persist(item, result)
        return result
