# Indexer: запись вердиктов в Postgres и индексация событий в Elasticsearch
import os
import json
import multiprocessing as mp

from common.bus import make_bus


def save_postgres(value):
    import psycopg2
    conn = psycopg2.connect(
        "dbname=%s user=%s password=%s host=%s port=%s" % (
            os.getenv("POSTGRES_DB", "moderation"),
            os.getenv("POSTGRES_USER", "mod"),
            os.getenv("POSTGRES_PASSWORD", "mod"),
            os.getenv("POSTGRES_HOST", "postgres"),
            os.getenv("POSTGRES_PORT", "5432")))
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO moderation_verdicts "
                "(post_id, decision, category, scores, reasons, policy, trace, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, now()) "
                "ON CONFLICT (post_id) DO UPDATE SET decision=EXCLUDED.decision, "
                "category=EXCLUDED.category, scores=EXCLUDED.scores, "
                "reasons=EXCLUDED.reasons, trace=EXCLUDED.trace",
                (value["post_id"], value["decision"], value["category"],
                 json.dumps(value.get("scores", {})), value.get("reasons", []),
                 value.get("policy", "standard"), value.get("trace", [])))
        conn.commit()
    finally:
        conn.close()


def save_es(value):
    from elasticsearch import Elasticsearch
    es = Elasticsearch(os.getenv("ES_URL", "http://elasticsearch:9200"))
    es.index(index="moderation-events", id=value["post_id"],
             document=json.loads(json.dumps(value, ensure_ascii=False)))


def process_event(bus, value):
    save_postgres(value)
    try:
        save_es(value)
    except Exception as e:
        print("[indexer] ES failed: %s" % e, flush=True)
    print("[indexer] stored %s (%s)" % (value["post_id"], value["decision"]), flush=True)


def kafka_loop():
    from confluent_kafka import Consumer
    c = Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        "group.id": "indexer-svc",
        "auto.offset.reset": "earliest",
    })
    c.subscribe(["moderation.events"])
    print("[indexer] kafka loop started", flush=True)
    while True:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
        process_event(None, json.loads(msg.value()))


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    if os.getenv("USE_INMEMORY_BUS") == "1":
        bus = make_bus()
        q = mp.Queue()
        bus.subscribe("moderation.events", q)
        while True:
            try:
                key, value = q.get(timeout=5)
            except Exception:
                continue
            process_event(bus, value)
    else:
        kafka_loop()
