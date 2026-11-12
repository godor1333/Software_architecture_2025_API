# Vision-сервис: классификация CLIP zero-shot + детект дубликатов по pHash
import os
import io
import multiprocessing as mp

import numpy as np
from PIL import Image

from common.bus import make_bus, InMemoryBus
from common.storage import make_storage
from services.vision.classifier import make_classifier


def phash(img, hash_size=8):
    # DCT-based pHash без внешних зависимостей
    im = img.convert("L").resize((32, 32), Image.LANCZOS)
    px = np.asarray(im, dtype=np.float64)
    dct = _dct2d(px)
    low = dct[:hash_size, :hash_size]
    med = np.median(low[1:, 1:])
    bits = (low > med).flatten()
    return "".join("1" if b else "0" for b in bits)


def _dct1d(v):
    N = len(v)
    n = np.arange(N)
    k = np.arange(N).reshape(-1, 1)
    return np.cos(np.pi * (2 * n + 1) * k / (2 * N)) @ v


def _dct2d(m):
    return _dct1d(_dct1d(m).T).T


def hamming(h1, h2):
    return sum(a != b for a, b in zip(h1, h2))


def process_event(bus, storage, classifier, seen, value, dup_distance=6):
    post_id = value["post_id"]
    data = storage.get_bytes(value["media_key"])
    img = Image.open(io.BytesIO(data))
    category, score, scores = classifier.predict(img)
    h = phash(img)
    duplicate_of = None
    for other_h, other_id in seen.items():
        if hamming(h, other_h) <= dup_distance:
            duplicate_of = other_id
            break
    if duplicate_of is None:
        seen[h] = post_id
    if duplicate_of is not None:
        category, score = "spam", max(score, 0.9)
    out = {
        "post_id": post_id,
        "category": category,
        "score": round(score, 4),
        "scores": {k: round(v, 4) for k, v in scores.items()},
        "duplicate": duplicate_of is not None,
        "duplicate_of": duplicate_of,
        "phash": h,
    }
    bus.publish("vision.verdicts", post_id, out)
    if hasattr(bus, "flush"):
        bus.flush()
    print("[vision] %s -> %s %.3f dup=%s" % (post_id, category, score, duplicate_of), flush=True)
    return out


def kafka_loop():
    from confluent_kafka import Consumer
    bus = make_bus()
    storage = make_storage()
    classifier = make_classifier()
    seen = {}
    c = Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        "group.id": "vision-svc",
        "auto.offset.reset": "earliest",
    })
    c.subscribe(["media.submitted"])
    print("[vision] kafka loop started", flush=True)
    while True:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
        value = json.loads(msg.value())
        process_event(bus, storage, classifier, seen, value)
        c.commit()


import json  # noqa: E402

if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    if os.getenv("USE_INMEMORY_BUS") == "1":
        bus = make_bus()
        q = mp.Queue()
        bus.subscribe("media.submitted", q)
        classifier = make_classifier()
        from common.storage import make_storage as ms
        seen = {}
        while True:
            try:
                key, value = q.get(timeout=5)
            except Exception:
                continue
            process_event(bus, ms(), classifier, seen, value)
    else:
        kafka_loop()
