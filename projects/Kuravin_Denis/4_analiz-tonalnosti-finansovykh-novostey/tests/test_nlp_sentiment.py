import pytest
from fastapi.testclient import TestClient
from project_4_financial_news_sentiment.api.main import app, pipeline, repository, risk_observer
from project_4_financial_news_sentiment.models import NewsItem, SentimentLabel, MarketTrend
from project_4_financial_news_sentiment.nlp.ner_extractor import FinancialNERExtractor
from project_4_financial_news_sentiment.nlp.sentiment_analyzer import FinBERTSentimentAnalyzer

client = TestClient(app)

def test_financial_ner():
    extractor = FinancialNERExtractor()
    text = "Совет директоров Сбербанка и руководство Газпрома обсудили партнерство с Яндексом."
    entities = extractor.extract_entities(text)
    tickers = {e.ticker for e in entities}

    assert "SBER" in tickers
    assert "GAZP" in tickers
    assert "YDEX" in tickers

def test_financial_sentiment_context():
    analyzer = FinBERTSentimentAnalyzer()

    # 1. Позитивный финансовый контекст
    label_pos, score_pos, _, drivers_pos = analyzer.analyze(
        "Компания зафиксировала рост чистой прибыли и рекордные дивиденды."
    )
    assert label_pos == SentimentLabel.POSITIVE
    assert score_pos > 0.4

    # 2. Негативный финансовый контекст
    label_neg, score_neg, _, drivers_neg = analyzer.analyze(
        "Холдинг отчитался о чистом убытке и снижении выручки из-за санкций."
    )
    assert label_neg == SentimentLabel.NEGATIVE
    assert score_neg < -0.4

    # 3. Финансовый парадокс: "падение издержек" — это позитив!
    label_cost, score_cost, _, _ = analyzer.analyze(
        "В отчетном квартале отмечено резкое падение издержек."
    )
    assert label_cost == SentimentLabel.POSITIVE
    assert score_cost > 0.2

def test_observer_alert():
    # Очищаем список алертов перед тестом
    risk_observer.triggered_alerts.clear()

    bad_news = NewsItem(
        title="Газпром допустил дефолт по внешним обязательствам",
        content="В отношении активов Газпрома введены блокирующие санкции, чистый убыток вырос."
    )
    pipeline.execute(bad_news)

    assert len(risk_observer.triggered_alerts) >= 1
    assert "GAZP" in risk_observer.triggered_alerts[-1]["tickers"]

def test_company_aggregation_trend():
    good_news = NewsItem(
        title="Сбербанк рекомендовал рекордные дивиденды",
        content="Сбер зафиксировал рост чистой прибыли на 30%."
    )
    pipeline.execute(good_news)

    agg = repository.get_company_sentiment("SBER")
    assert agg.total_news_count >= 1
    assert agg.positive_count >= 1
    assert agg.sentiment_index > 0.0
    assert agg.market_trend == MarketTrend.BULLISH

def test_api_endpoints():
    # 1. Health
    h_resp = client.get("/api/v1/health")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "healthy"

    # 2. Analyze
    payload = {
        "title": "Nvidia объявила байбэк на рекордную сумму",
        "content": "Руководство NVDA утвердило выкуп акций на фоне превышения прогнозов выручки."
    }
    resp = client.post("/api/v1/news/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_sentiment"] == "POSITIVE"
    assert any(e["ticker"] == "NVDA" for e in data["entities"])

    # 3. Overview
    o_resp = client.get("/api/v1/sentiment/overview")
    assert o_resp.status_code == 200
    assert len(o_resp.json()) >= 1
