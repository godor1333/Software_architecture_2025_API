from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, status

from app.config import Settings, TOPIC_ORDERS_CREATED
from app.dashboard import dashboard_page
from app.events import KafkaEventBus
from app.ml import LightGBMAdapter
from app.resilience import CircuitBreaker, CircuitOpenError
from app.schemas import DashboardSummary, OrderEvent, OrderSubmission, ScoreResponse
from app.scoring import default_rule_chain
from app.services import ScoringService
from app.storage import (
    ClickHouseAnalyticsStore,
    InMemoryAnalyticsStore,
    InMemoryCounterStore,
    InMemoryScoreStore,
    PostgresScoreStore,
    RedisCounterStore,
)


MODEL_PATH = Path(os.getenv("MODEL_PATH", "artifacts/lightgbm_fraud_model.txt"))
settings = Settings.from_env()
ml_adapter = LightGBMAdapter(MODEL_PATH) if MODEL_PATH.exists() else None


def build_service(active_settings: Settings | None = None) -> ScoringService:
    active_settings = active_settings or Settings.from_env()
    if active_settings.app_mode == "distributed":
        counters = RedisCounterStore(active_settings.redis_url)
        scores = PostgresScoreStore(active_settings.postgres_dsn)
        analytics = ClickHouseAnalyticsStore(
            active_settings.clickhouse_host,
            active_settings.clickhouse_port,
            active_settings.clickhouse_user,
            active_settings.clickhouse_password,
        )
    else:
        counters = InMemoryCounterStore()
        scores = InMemoryScoreStore()
        analytics = InMemoryAnalyticsStore()
    return ScoringService(active_settings, default_rule_chain(), ml_adapter, counters, scores, analytics)


def build_app(active_settings: Settings | None = None) -> FastAPI:
    active_settings = active_settings or settings
    service = build_service(active_settings)
    event_bus = KafkaEventBus(active_settings.kafka_bootstrap_servers) if active_settings.app_mode == "distributed" else None
    kafka_circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=10)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await service.scores.initialize()
        await service.analytics.initialize()
        if event_bus is not None:
            await event_bus.start()
        try:
            yield
        finally:
            if event_bus is not None:
                await event_bus.stop()
            await service.counters.close()
            await service.scores.close()
            await service.analytics.close()

    application = FastAPI(
        title="TicketShield Anti-Fraud API",
        version="2.0.0",
        description="Сервис риск-скоринга заказов концертных билетов. В Docker запускает Kafka pipeline.",
        lifespan=lifespan,
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "model_version": active_settings.model_version,
            "scoring_mode": "lightgbm" if ml_adapter else "rules",
            "app_mode": active_settings.app_mode,
        "kafka_circuit": kafka_circuit_breaker.state.value if event_bus is not None else "NOT_USED",
        }

    @application.post(
        "/api/v1/orders/score",
        response_model=ScoreResponse | OrderSubmission,
        status_code=status.HTTP_201_CREATED,
    )
    async def score_order(event: OrderEvent) -> ScoreResponse | OrderSubmission:
        """Local mode returns a decision; distributed mode publishes orders.created."""
        if event_bus is not None:
            try:
                await kafka_circuit_breaker.call(
                    lambda: event_bus.publish(TOPIC_ORDERS_CREATED, event.model_dump(mode="json"))
                )
            except CircuitOpenError as error:
                raise HTTPException(status_code=503, detail="Kafka временно недоступна: circuit открыт") from error
            except Exception as error:
                raise HTTPException(status_code=503, detail="Kafka недоступна, заказ не опубликован") from error
            return OrderSubmission(
                order_id=event.order_id,
                message="Заказ опубликован в Kafka topic orders.created и ожидает обработки.",
            )
        enriched = await service.enrich(event)
        return await service.score(enriched)

    @application.get("/api/v1/orders/{order_id}", response_model=ScoreResponse)
    async def get_score(order_id: str) -> ScoreResponse:
        result = await service.scores.get_score(order_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Решение для заказа не найдено")
        return result

    @application.get("/api/v1/dashboard/summary", response_model=DashboardSummary)
    async def dashboard_summary() -> DashboardSummary:
        return await service.analytics.summary(active_settings.model_version)

    @application.get("/dashboard", include_in_schema=False)
    async def dashboard():
        return dashboard_page()

    return application


app = build_app()
