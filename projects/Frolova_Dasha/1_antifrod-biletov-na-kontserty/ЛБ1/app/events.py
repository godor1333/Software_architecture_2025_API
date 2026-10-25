from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


JsonMessage = dict[str, Any]


def encode_message(message: JsonMessage) -> bytes:
    """Serialize events deterministically and preserve Russian text in UTF-8."""
    return json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def decode_message(value: bytes) -> JsonMessage:
    return json.loads(value.decode("utf-8"))


class KafkaEventBus:
    """Adapter over aiokafka used by API and workers."""

    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if self._producer is None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=encode_message,
            )
            await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(self, topic: str, message: JsonMessage) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started")
        await self._producer.send_and_wait(topic, message)

    async def consume_forever(
        self,
        topic: str,
        group_id: str,
        handler: Callable[[JsonMessage], Awaitable[None]],
    ) -> None:
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=group_id,
            value_deserializer=decode_message,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await consumer.start()
        try:
            async for record in consumer:
                await handler(record.value)
        finally:
            await consumer.stop()
