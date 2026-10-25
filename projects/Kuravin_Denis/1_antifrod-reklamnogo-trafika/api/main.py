import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from ..models import (
    ClickEvent,
    FraudEvaluationResult,
    BatchClickRequest,
    BatchClickResponse,
    AntifraudMetrics
)
from ..config import settings
from ..patterns.chain_of_responsibility import (
    EvaluationContext,
    BlacklistIpHandler,
    UserAgentBotHandler,
    FastClickRateLimitHandler,
    ScoringStrategyHandler
)
from ..patterns.strategy import (
    IScoringStrategy,
    HybridScoringStrategy,
    MLOnlyStrategy,
    RuleBasedStrategy
)
from ..patterns.repository import InMemoryClickRepository, IClickRepository
from ..patterns.circuit_breaker import CircuitBreaker

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Высоконагруженный сервис антифрода рекламного трафика (Clickstream ML + Rule Engine)"
)

# Инфраструктурные зависимости
repository: IClickRepository = InMemoryClickRepository()
circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_time_sec=10.0)

# Текущая стратегия и цепочка обязанностей
current_strategy: IScoringStrategy = HybridScoringStrategy()

def build_chain(strategy: IScoringStrategy) -> BlacklistIpHandler:
    h1 = BlacklistIpHandler()
    h2 = UserAgentBotHandler()
    h3 = FastClickRateLimitHandler()
    h4 = ScoringStrategyHandler(strategy)

    h1.set_next(h2).set_next(h3).set_next(h4)
    return h1

chain_root = build_chain(current_strategy)

def evaluate_click_pipeline(event: ClickEvent) -> FraudEvaluationResult:
    start_time = time.time()

    # Получаем частотность из репозитория
    c_1min, c_5min = repository.get_ip_frequency(event.ip_address)
    ctx = EvaluationContext(event, ip_clicks_1min=c_1min, ip_clicks_5min=c_5min)

    # Прогон через цепочку обязанностей
    result = chain_root.handle(ctx)
    if result is None:
        raise RuntimeError("Chain did not produce a result")

    elapsed = (time.time() - start_time) * 1000.0
    result.processing_time_ms = round(elapsed, 2)

    # Сохраняем в репозиторий
    repository.record_click(event, result)
    return result

@app.post("/api/v1/clicks/evaluate", response_model=FraudEvaluationResult, tags=["Scoring"])
def evaluate_click(event: ClickEvent):
    """Синхронная проверка клика через цепочку обязанностей и скоринг."""
    return evaluate_click_pipeline(event)

@app.post("/api/v1/clicks/batch", response_model=BatchClickResponse, tags=["Scoring"])
def evaluate_batch(batch: BatchClickRequest):
    """Пакетная обработка кликов (например, при чтении из Kafka batch)."""
    results: List[FraudEvaluationResult] = []
    allowed = 0
    suspicious = 0
    blocked = 0

    for ev in batch.events:
        res = evaluate_click_pipeline(ev)
        results.append(res)
        if res.status == "ALLOWED":
            allowed += 1
        elif res.status == "SUSPICIOUS":
            suspicious += 1
        else:
            blocked += 1

    return BatchClickResponse(
        total=len(results),
        allowed_count=allowed,
        suspicious_count=suspicious,
        blocked_count=blocked,
        results=results
    )

@app.get("/api/v1/metrics", response_model=AntifraudMetrics, tags=["Analytics"])
def get_metrics():
    """Сводные метрики антифрод-системы (процент фрода, задержка, топ IP)."""
    return repository.get_metrics()

@app.get("/api/v1/recent", response_model=List[FraudEvaluationResult], tags=["Analytics"])
def get_recent(limit: int = Query(20, ge=1, le=100)):
    """Последние проверенные события."""
    return repository.get_recent_results(limit)

@app.post("/api/v1/strategy", tags=["Configuration"])
def switch_strategy(mode: str = Query(..., pattern="^(hybrid|ml_only|rules_only)$")):
    """Динамическое переключение стратегии скоринга (Strategy Pattern)."""
    global current_strategy, chain_root
    if mode == "hybrid":
        current_strategy = HybridScoringStrategy()
    elif mode == "ml_only":
        current_strategy = MLOnlyStrategy()
    elif mode == "rules_only":
        current_strategy = RuleBasedStrategy()
    chain_root = build_chain(current_strategy)
    return {"status": "success", "new_strategy": mode}

@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Проверка жизнеспособности сервиса и статуса Circuit Breaker."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "circuit_breaker_state": circuit_breaker.state,
        "environment": settings.environment
    }
