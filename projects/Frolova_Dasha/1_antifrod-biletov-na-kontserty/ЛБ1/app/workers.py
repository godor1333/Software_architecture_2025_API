from __future__ import annotations

import asyncio

from app.config import (
    GROUP_ANALYTICS,
    GROUP_FEATURES,
    GROUP_SCORING,
    TOPIC_DECISIONS,
    TOPIC_ORDERS_CREATED,
    TOPIC_ORDERS_ENRICHED,
    Settings,
)
from app.events import KafkaEventBus
from app.main import build_service
from app.schemas import OrderEvent, ScoreResponse


async def run_feature_worker() -> None:
    """Consumer group feature-service: enriches orders with Redis features."""
    settings = Settings.from_env()
    service = build_service(settings)
    bus = KafkaEventBus(settings.kafka_bootstrap_servers)
    await service.scores.initialize()
    await service.analytics.initialize()
    await bus.start()

    async def handle(payload: dict) -> None:
        enriched = await service.enrich(OrderEvent.model_validate(payload))
        await service.scores.save_order(enriched)
        await bus.publish(TOPIC_ORDERS_ENRICHED, enriched.model_dump(mode="json"))

    try:
        await bus.consume_forever(TOPIC_ORDERS_CREATED, GROUP_FEATURES, handle)
    finally:
        await bus.stop()
        await service.counters.close()
        await service.scores.close()
        await service.analytics.close()


async def run_scoring_worker() -> None:
    """Consumer group scoring-service: persists decision and emits it to Kafka."""
    settings = Settings.from_env()
    service = build_service(settings)
    bus = KafkaEventBus(settings.kafka_bootstrap_servers)
    await service.scores.initialize()
    await service.analytics.initialize()
    await bus.start()

    async def handle(payload: dict) -> None:
        result = await service.score(OrderEvent.model_validate(payload))
        await bus.publish(TOPIC_DECISIONS, result.model_dump(mode="json"))

    try:
        await bus.consume_forever(TOPIC_ORDERS_ENRICHED, GROUP_SCORING, handle)
    finally:
        await bus.stop()
        await service.counters.close()
        await service.scores.close()
        await service.analytics.close()


async def run_analytics_worker() -> None:
    """Independent analytics consumer group for antifraud.decisions."""
    settings = Settings.from_env()
    service = build_service(settings)
    bus = KafkaEventBus(settings.kafka_bootstrap_servers)
    await service.scores.initialize()
    await service.analytics.initialize()

    async def handle(payload: dict) -> None:
        # Validation leaves an independently scalable extension point for BI export.
        ScoreResponse.model_validate(payload)

    try:
        await bus.consume_forever(TOPIC_DECISIONS, GROUP_ANALYTICS, handle)
    finally:
        await service.counters.close()
        await service.scores.close()
        await service.analytics.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="TicketShield Kafka workers")
    parser.add_argument("role", choices=("feature", "scoring", "analytics"))
    role = parser.parse_args().role
    runners = {
        "feature": run_feature_worker,
        "scoring": run_scoring_worker,
        "analytics": run_analytics_worker,
    }
    asyncio.run(runners[role]())


if __name__ == "__main__":
    main()
