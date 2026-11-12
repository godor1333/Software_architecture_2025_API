# Text-сервис: анализ текста публикации (abuse / scam_text / clean)
import os
import multiprocessing as mp

from common.bus import make_bus
from services.text.classifier import make_classifier


def process_event(bus, classifier, value):
    post_id = value["post_id"]
    cat, score = classifier.predict(value.get("text", ""))
    out = {"post_id": post_id, "category": cat, "score": round(score, 4)}
    bus.publish("text.verdicts", post_id, out)
    if hasattr(bus, "flush"):
        bus.flush()
    print("[text] %s -> %s %.3f" % (post_id, cat, score), flush=True)
    return out


def kafka_loop():
    import json
    from confluent_kafka import Consumer
    bus = make_bus()
    classifier = make_classifier()
    c = Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        "group.id": "text-svc",
        "auto.offset.reset": "earliest",
    })
    c.subscribe(["media.submitted"])
    print("[text] kafka loop started", flush=True)
    while True:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
        process_event(bus, classifier, json.loads(msg.value()))
        c.commit()


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    if os.getenv("USE_INMEMORY_BUS") == "1":
        bus = make_bus()
        q = mp.Queue()
        bus.subscribe("media.submitted", q)
        classifier = make_classifier()
        while True:
            try:
                key, value = q.get(timeout=5)
            except Exception:
                continue
            process_event(bus, classifier, value)
    else:
        kafka_loop()
