"""Metrics-сервис: Kafka consumer, складывающий события в PostgreSQL."""
import json
import logging
import time

import psycopg2
from kafka import KafkaConsumer

from src.common.config import settings
from src.common.log import setup
from src.common.schemas import (
    GROUP_METRICS,
    TOPIC_CHECKPOINTS,
    TOPIC_EPISODES,
    TOPIC_PREDICTIONS,
)

log = setup()

SQL_EPISODE = """INSERT INTO episodes
    (experiment_id, run_id, episode, steps, reward, epsilon, loss)
    VALUES (%s, %s, %s, %s, %s, %s, %s)"""
SQL_CHECKPOINT = """INSERT INTO checkpoints
    (experiment_id, run_id, step, artifact_uri) VALUES (%s, %s, %s, %s)"""
SQL_PREDICTION = """INSERT INTO inference_logs
    (request_id, model_name, action, action_name, latency_ms)
    VALUES (%s, %s, %s, %s, %s)"""


def get_conn():
    for attempt in range(10):
        try:
            return psycopg2.connect(settings.postgres_dsn)
        except psycopg2.OperationalError as exc:
            log.warning("postgres not ready (%d/10): %s", attempt + 1, exc)
            time.sleep(3)
    raise RuntimeError("postgres unavailable")


def main() -> None:
    conn = get_conn()
    consumer = KafkaConsumer(
        TOPIC_EPISODES,
        TOPIC_CHECKPOINTS,
        TOPIC_PREDICTIONS,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=GROUP_METRICS,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    log.info("metrics consumer started: topics=%s group=%s",
             [TOPIC_EPISODES, TOPIC_CHECKPOINTS, TOPIC_PREDICTIONS], GROUP_METRICS)
    with conn.cursor() as cur:
        for msg in consumer:
            row = msg.value
            try:
                if msg.topic == TOPIC_EPISODES:
                    cur.execute(SQL_EPISODE, (
                        row["experiment_id"], row["run_id"], row["episode"],
                        row["steps"], row["reward"], row["epsilon"], row["loss"]))
                elif msg.topic == TOPIC_CHECKPOINTS:
                    cur.execute(SQL_CHECKPOINT, (
                        row["experiment_id"], row["run_id"], row["step"],
                        row["artifact_uri"]))
                elif msg.topic == TOPIC_PREDICTIONS:
                    cur.execute(SQL_PREDICTION, (
                        row["request_id"], row["model_name"], row["action"],
                        row["action_name"], row["latency_ms"]))
                conn.commit()
            except Exception as exc:  # noqa: BLE001
                log.exception("insert failed for %s: %s", msg.topic, exc)
                conn.rollback()


if __name__ == "__main__":
    main()
