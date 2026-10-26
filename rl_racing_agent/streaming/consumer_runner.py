<<<<<<< HEAD
import os
import signal
import time
from streaming.consumer import TelemetryConsumer
from db.writer import TelemetryWriter


BATCH_SIZE = 50
FLUSH_INTERVAL = 2.0  # секунд


def run():
    dsn = os.getenv("DATABASE_URL", "postgresql://rl:rl@localhost:5432/racing")
    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

    writer = TelemetryWriter(dsn)
    consumer = TelemetryConsumer(bootstrap_servers=bootstrap)

    print("[consumer_runner] started, waiting for events...")

    buffer = []
    last_flush = time.time()

    def flush():
        nonlocal buffer, last_flush
        if buffer:
            writer.write_batch(buffer)
            print(f"[consumer_runner] flushed {len(buffer)} events")
            buffer = []
        last_flush = time.time()

    try:
        for event in consumer:
            buffer.append(event)
            if len(buffer) >= BATCH_SIZE or (time.time() - last_flush) >= FLUSH_INTERVAL:
                flush()
    except KeyboardInterrupt:
        print("[consumer_runner] stopping...")
    finally:
        flush()
        print("[consumer_runner] done")


if __name__ == "__main__":
=======
import os
import signal
import time
from streaming.consumer import TelemetryConsumer
from db.writer import TelemetryWriter


BATCH_SIZE = 50
FLUSH_INTERVAL = 2.0  # секунд


def run():
    dsn = os.getenv("DATABASE_URL", "postgresql://rl:rl@localhost:5432/racing")
    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

    writer = TelemetryWriter(dsn)
    consumer = TelemetryConsumer(bootstrap_servers=bootstrap)

    print("[consumer_runner] started, waiting for events...")

    buffer = []
    last_flush = time.time()

    def flush():
        nonlocal buffer, last_flush
        if buffer:
            writer.write_batch(buffer)
            print(f"[consumer_runner] flushed {len(buffer)} events")
            buffer = []
        last_flush = time.time()

    try:
        for event in consumer:
            buffer.append(event)
            if len(buffer) >= BATCH_SIZE or (time.time() - last_flush) >= FLUSH_INTERVAL:
                flush()
    except KeyboardInterrupt:
        print("[consumer_runner] stopping...")
    finally:
        flush()
        print("[consumer_runner] done")


if __name__ == "__main__":
>>>>>>> 0037982a52b70d8ed1ac0df57ec0f7ee8fcf872b
    run()