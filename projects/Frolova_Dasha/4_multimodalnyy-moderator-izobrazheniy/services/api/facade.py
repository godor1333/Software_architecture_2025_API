# Паттерн Facade: единая точка входа для ingestion, чтения вердиктов и статистики
import os
import json
import datetime

import psycopg2
import psycopg2.extras

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

class ModeratorFacade:
    # Прячет от клиента: bus + storage + базу. Клиент знает только этот класс.
    def __init__(self, bus, storage):
        self.bus = bus
        self.storage = storage
        self._pg = None

    def _dsn(self):
        return "dbname=%s user=%s password=%s host=%s port=%s" % (
            os.getenv("POSTGRES_DB", "moderation"),
            os.getenv("POSTGRES_USER", "mod"),
            os.getenv("POSTGRES_PASSWORD", "mod"),
            os.getenv("POSTGRES_HOST", "postgres"),
            os.getenv("POSTGRES_PORT", "5432"),
        )

    def submit_post(self, post_id, user_id, media_key, text):
        event = {
            "post_id": post_id,
            "user_id": user_id,
            "media_key": media_key,
            "text": text,
            "created_at": now_iso(),
        }
        self.bus.publish("media.submitted", post_id, event)
        self.bus.flush() if hasattr(self.bus, "flush") else None
        return event

    def store_image(self, post_id, filename, data):
        key = "posts/%s/%s" % (post_id, filename)
        self.storage.put_bytes(key, data)
        return key

    def get_verdict(self, post_id):
        conn = psycopg2.connect(self._dsn())
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM moderation_verdicts WHERE post_id = %s", (post_id,))
                return cur.fetchone()
        finally:
            conn.close()

    def stats(self):
        conn = psycopg2.connect(self._dsn())
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT decision, count(*) FROM moderation_verdicts GROUP BY decision"
                )
                rows = cur.fetchall()
            return {r[0]: r[1] for r in rows}
        finally:
            conn.close()

    def search(self, query, size=10):
        from elasticsearch import Elasticsearch
        es = Elasticsearch(os.getenv("ES_URL", "http://elasticsearch:9200"))
        body = {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"text": query}},
                        {"match": {"category": query}},
                        {"match": {"decision": query}},
                    ]
                }
            },
            "size": size,
        }
        res = es.search(index="moderation-events", body=body)
        return [h["_source"] for h in res["hits"]["hits"]]
