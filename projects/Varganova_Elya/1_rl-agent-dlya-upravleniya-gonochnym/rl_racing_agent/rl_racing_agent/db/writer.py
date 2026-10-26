import psycopg2
from psycopg2.extras import execute_values
from streaming.events import TelemetryEvent


class TelemetryWriter:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._ensure_table()

    def _ensure_table(self):
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS telemetry (
                        id SERIAL PRIMARY KEY,
                        episode INT,
                        step INT,
                        reward REAL,
                        speed REAL,
                        progress REAL,
                        crashed BOOLEAN,
                        timestamp TIMESTAMP
                    )
                """)
            conn.commit()

    def write_batch(self, events: list[TelemetryEvent]):
        if not events:
            return
        rows = [
            (e.episode, e.step, e.reward, e.speed, e.progress, e.crashed, e.timestamp)
            for e in events
        ]
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    "INSERT INTO telemetry (episode, step, reward, speed, progress, crashed, timestamp) VALUES %s",
                    rows,
                )
            conn.commit()