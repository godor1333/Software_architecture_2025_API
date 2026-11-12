# Fusion-сервис: join двух модальностей + policy engine + публикация события
import os
import time
import json
import multiprocessing as mp

from common.bus import make_bus
from common.schemas import ModerationVerdict
from services.fusion.policies import get_policy
from services.fusion.chain import build_chain
from services.fusion.observers import MetricsObserver, AuditLogObserver, WebhookObserver

JOIN_TIMEOUT = 15.0


def decide(policy, vision, text):
    verdict = ModerationVerdict(post_id=vision["post_id"], decision="approve",
                                policy=policy.name)
    verdict.scores = {
        "vision_category": vision["category"],
        "vision_score": vision["score"],
        "text_category": text["category"],
        "text_score": text["score"],
    }
    ctx = {
        "verdict": verdict,
        "policy": policy,
        "vision_cat": vision["category"],
        "vision_score": vision["score"],
        "text_cat": text["category"],
        "text_score": text["score"],
        "duplicate": vision.get("duplicate", False),
        "duplicate_of": vision.get("duplicate_of"),
    }
    chain = build_chain()
    chain.handle(ctx)
    return verdict


def kafka_loop():
    bus = make_bus()
    from confluent_kafka import Consumer
    policy_name = os.getenv("POLICY", "standard")
    policy = get_policy(policy_name)
    observers = [MetricsObserver(), AuditLogObserver(),
                 WebhookObserver(os.getenv("WEBHOOK_URL"))]
    c = Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        "group.id": "fusion-svc",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    c.subscribe(["vision.verdicts", "text.verdicts"])
    print("[fusion] kafka loop started, policy=%s" % policy.name, flush=True)
    pending = {}
    last_commit = time.time()
    while True:
        msg = c.poll(0.5)
        if msg and not msg.error():
            value = json.loads(msg.value())
            pid = value["post_id"]
            slot = pending.setdefault(pid, {})
            slot["vision" if "vision" in msg.topic() else "text"] = value
        # join: оба вердикта либо таймаут
        now = time.time()
        for pid in list(pending):
            slot = pending[pid]
            if "vision" in slot and "text" in slot:
                ready, expire = True, False
            elif now - slot.get("seen_at", now) > JOIN_TIMEOUT:
                ready, expire = True, True
            else:
                ready, expire = False, False
            if not ready:
                slot.setdefault("seen_at", now)
                continue
            vision = slot.get("vision", {"post_id": pid, "category": "benign",
                                         "score": 0.0, "duplicate": False, "duplicate_of": None})
            text = slot.get("text", {"post_id": pid, "category": "clean", "score": 0.0})
            verdict = decide(policy, vision, text)
            for obs in observers:
                obs.on_verdict(verdict)
            bus.publish("moderation.events", pid, verdict.to_dict())
            if hasattr(bus, "flush"):
                bus.flush()
            pending.pop(pid, None)
        if now - last_commit > 3:
            try:
                c.commit()
            except Exception:
                pass
            last_commit = now


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    if os.getenv("USE_INMEMORY_BUS") == "1":
        bus = make_bus()
        policy = get_policy(os.getenv("POLICY", "standard"))
        observers = [MetricsObserver(), AuditLogObserver()]
        q_v = mp.Queue(); q_t = mp.Queue()
        bus.subscribe("vision.verdicts", q_v)
        bus.subscribe("text.verdicts", q_t)
        pending = {}
        while True:
            got = False
            for q, kind in ((q_v, "vision"), (q_t, "text")):
                try:
                    key, value = q.get(timeout=0.2)
                    pending.setdefault(value["post_id"], {})[kind] = value
                    got = True
                except Exception:
                    pass
            for pid in list(pending):
                slot = pending[pid]
                if "vision" in slot and "text" in slot:
                    verdict = decide(policy, slot["vision"], slot["text"])
                    for obs in observers:
                        obs.on_verdict(verdict)
                    bus.publish("moderation.events", pid, verdict.to_dict())
                    pending.pop(pid, None)
    else:
        kafka_loop()
