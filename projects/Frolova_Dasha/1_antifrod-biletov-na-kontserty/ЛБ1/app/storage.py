from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Protocol

import asyncpg
import clickhouse_connect
import redis.asyncio as redis

from app.schemas import DashboardSummary, Decision, OrderEvent, RuleHit, ScoreResponse


POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(64) PRIMARY KEY,
    event_id VARCHAR(64) NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    ticket_count INTEGER NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_account_created
    ON orders(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_device_created
    ON orders(device_id, created_at DESC);
CREATE TABLE IF NOT EXISTS fraud_decisions (
    order_id VARCHAR(64) PRIMARY KEY REFERENCES orders(order_id),
    risk_score DOUBLE PRECISION NOT NULL,
    decision VARCHAR(16) NOT NULL,
    reasons JSONB NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    scored_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decisions_review_scored
    ON fraud_decisions(decision, scored_at DESC);
"""

CLICKHOUSE_SCHEMA = """
CREATE TABLE IF NOT EXISTS antifraud_events (
    event_date Date,
    scored_at DateTime,
    order_id String,
    event_id String,
    decision LowCardinality(String),
    risk_score Float64,
    model_version LowCardinality(String),
    reason_codes Array(String)
) ENGINE = MergeTree
PARTITION BY event_date
ORDER BY (event_date, decision, order_id)
"""


class CounterStore(Protocol):
    async def enrich(self, event: OrderEvent) -> OrderEvent: ...

    async def close(self) -> None: ...


class RedisCounterStore:
    """Feature Store: ephemeral velocity and device/account linkage counters."""

    def __init__(self, redis_url: str) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    async def enrich(self, event: OrderEvent) -> OrderEvent:
        velocity_key = f"velocity:{event.account_id}:10m"
        device_key = f"device_accounts:{event.device_id}:24h"
        async with self._client.pipeline(transaction=True) as pipeline:
            pipeline.incr(velocity_key)
            pipeline.expire(velocity_key, 600)
            pipeline.sadd(device_key, event.account_id)
            pipeline.expire(device_key, 86400)
            pipeline.scard(device_key)
            values = await pipeline.execute()
        return event.model_copy(
            update={
                "purchase_attempts_10m": max(event.purchase_attempts_10m, int(values[0])),
                "device_accounts_24h": max(event.device_accounts_24h, int(values[4])),
            }
        )

    async def close(self) -> None:
        await self._client.aclose()


class InMemoryCounterStore:
    """Local fallback that keeps single-process development functional."""

    async def enrich(self, event: OrderEvent) -> OrderEvent:
        return event

    async def close(self) -> None:
        return None


class ScoreStore(Protocol):
    async def initialize(self) -> None: ...

    async def save_order(self, event: OrderEvent) -> None: ...

    async def save_score(self, result: ScoreResponse) -> None: ...

    async def get_score(self, order_id: str) -> ScoreResponse | None: ...

    async def close(self) -> None: ...


class PostgresScoreStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        async with self._pool.acquire() as connection:
            await connection.execute(POSTGRES_SCHEMA)

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PostgreSQL pool is not initialized")
        return self._pool

    async def save_order(self, event: OrderEvent) -> None:
        pool = self._require_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                """INSERT INTO orders(order_id, event_id, account_id, device_id, amount, ticket_count, payload, created_at)
                   VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
                   ON CONFLICT (order_id) DO NOTHING""",
                event.order_id, event.event_id, event.account_id, event.device_id,
                event.amount, event.ticket_count, event.model_dump_json(), event.occurred_at,
            )

    async def save_score(self, result: ScoreResponse) -> None:
        pool = self._require_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                """INSERT INTO fraud_decisions(order_id, risk_score, decision, reasons, model_version, scored_at)
                   VALUES($1,$2,$3,$4::jsonb,$5,$6)
                   ON CONFLICT (order_id) DO UPDATE SET risk_score=EXCLUDED.risk_score,
                   decision=EXCLUDED.decision, reasons=EXCLUDED.reasons,
                   model_version=EXCLUDED.model_version, scored_at=EXCLUDED.scored_at""",
                result.order_id, result.risk_score, result.decision.value,
                json.dumps([item.model_dump() for item in result.reasons], ensure_ascii=False),
                result.model_version, result.scored_at,
            )

    async def get_score(self, order_id: str) -> ScoreResponse | None:
        pool = self._require_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT order_id, risk_score, decision, reasons, model_version, scored_at FROM fraud_decisions WHERE order_id=$1",
                order_id,
            )
        if row is None:
            return None
        reasons = row["reasons"]
        if isinstance(reasons, str):
            reasons = json.loads(reasons)
        return ScoreResponse(
            order_id=row["order_id"], risk_score=row["risk_score"],
            decision=Decision(row["decision"]),
            reasons=[RuleHit(**item) for item in reasons],
            model_version=row["model_version"], scored_at=row["scored_at"],
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


class InMemoryScoreStore:
    def __init__(self) -> None:
        self._orders: dict[str, OrderEvent] = {}
        self._scores: dict[str, ScoreResponse] = {}

    async def initialize(self) -> None:
        return None

    async def save_order(self, event: OrderEvent) -> None:
        self._orders[event.order_id] = event

    async def save_score(self, result: ScoreResponse) -> None:
        self._scores[result.order_id] = result

    async def get_score(self, order_id: str) -> ScoreResponse | None:
        return self._scores.get(order_id)

    async def close(self) -> None:
        return None


class AnalyticsStore(Protocol):
    async def initialize(self) -> None: ...

    async def write(self, event: OrderEvent, result: ScoreResponse) -> None: ...

    async def summary(self, model_version: str) -> DashboardSummary: ...

    async def close(self) -> None: ...


class ClickHouseAnalyticsStore:
    def __init__(self, host: str, port: int, username: str = "default", password: str = "") -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._client = None

    async def initialize(self) -> None:
        self._client = await asyncio.to_thread(
            clickhouse_connect.get_client,
            host=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            database="antifraud",
        )
        await asyncio.to_thread(self._client.command, CLICKHOUSE_SCHEMA)

    def _require_client(self):
        if self._client is None:
            raise RuntimeError("ClickHouse client is not initialized")
        return self._client

    async def write(self, event: OrderEvent, result: ScoreResponse) -> None:
        client = self._require_client()
        row = [[
            result.scored_at.date(), result.scored_at.replace(tzinfo=None), result.order_id,
            event.event_id, result.decision.value, result.risk_score, result.model_version,
            [hit.code for hit in result.reasons],
        ]]
        await asyncio.to_thread(
            client.insert, "antifraud_events", row,
            column_names=["event_date", "scored_at", "order_id", "event_id", "decision", "risk_score", "model_version", "reason_codes"],
        )

    async def summary(self, model_version: str) -> DashboardSummary:
        client = self._require_client()
        query = """
            SELECT count(), countIf(decision = 'REVIEW'), avg(risk_score)
            FROM antifraud_events
            WHERE model_version = {model_version:String}
        """
        result = await asyncio.to_thread(client.query, query, parameters={"model_version": model_version})
        total, review, average = result.result_rows[0]
        return DashboardSummary(
            total_events=int(total), review_events=int(review),
            review_rate=round(float(review) / total, 4) if total else 0.0,
            average_risk_score=round(float(average or 0.0), 4), model_version=model_version,
        )

    async def close(self) -> None:
        if self._client is not None:
            await asyncio.to_thread(self._client.close)
            self._client = None


class InMemoryAnalyticsStore:
    def __init__(self) -> None:
        self._items: list[tuple[OrderEvent, ScoreResponse]] = []

    async def initialize(self) -> None:
        return None

    async def write(self, event: OrderEvent, result: ScoreResponse) -> None:
        self._items.append((event, result))

    async def summary(self, model_version: str) -> DashboardSummary:
        results = [result for _, result in self._items if result.model_version == model_version]
        total = len(results)
        review = sum(result.decision == Decision.REVIEW for result in results)
        average = sum(result.risk_score for result in results) / total if total else 0.0
        return DashboardSummary(
            total_events=total, review_events=review, review_rate=round(review / total, 4) if total else 0.0,
            average_risk_score=round(average, 4), model_version=model_version,
        )

    async def close(self) -> None:
        return None
