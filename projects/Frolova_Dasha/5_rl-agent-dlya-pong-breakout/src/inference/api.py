"""Inference-сервис: FastAPI поверх обученной политики."""
import json
import logging
import os
import time
import uuid

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List

from src.agents.factory import AgentFactory
from src.common.config import settings
from src.common.schemas import ACTION_NAMES, PredictionEvent, TOPIC_PREDICTIONS

log = logging.getLogger("pong.inference")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Pong RL Inference API", version="1.0.0")
_state = {"strategy": None, "name": None, "producer": None}


@app.on_event("startup")
def load_model() -> None:
    meta_path = settings.model_path + ".meta.json"
    if not (os.path.exists(settings.model_path) and os.path.exists(meta_path)):
        log.warning("model not found at %s — /predict вернёт 503", settings.model_path)
        return
    with open(meta_path, encoding="utf-8") as f:
        algorithm = json.load(f)["algorithm"]
    _state["strategy"] = AgentFactory.load(algorithm, settings.model_path)
    _state["name"] = algorithm
    log.info("model loaded: %s (%s)", settings.model_path, algorithm)


class PredictRequest(BaseModel):
    observation: List[List[List[int]]] = Field(
        ..., description="Стек 4 кадров 84x84, значения 0..255"
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": _state["strategy"] is not None,
        "model": _state["name"],
    }


@app.get("/model/info")
def model_info():
    if _state["strategy"] is None:
        raise HTTPException(503, "model not trained yet")
    return {
        "algorithm": _state["name"],
        "model_path": settings.model_path,
        "observation_shape": [4, 84, 84],
        "actions": ACTION_NAMES,
    }


@app.post("/predict")
def predict(req: PredictRequest):
    if _state["strategy"] is None:
        raise HTTPException(503, "model not trained yet — запустите trainer")
    try:
        obs = np.asarray(req.observation, dtype=np.uint8)
    except (ValueError, TypeError):
        raise HTTPException(422, "observation must be numeric array")
    if obs.shape != (4, 84, 84):
        raise HTTPException(422, f"expected shape (4, 84, 84), got {obs.shape}")

    t0 = time.perf_counter()
    action, _ = _state["strategy"].predict(obs, deterministic=True)
    latency_ms = (time.perf_counter() - t0) * 1000

    event = PredictionEvent(
        request_id=uuid.uuid4().hex[:12],
        model_name=_state["name"],
        action=int(action),
        action_name=ACTION_NAMES[int(action)],
        latency_ms=round(latency_ms, 3),
        ts=time.time(),
    )
    _publish(event)
    return {
        "request_id": event.request_id,
        "action": event.action,
        "action_name": event.action_name,
        "latency_ms": event.latency_ms,
        "model": _state["name"],
    }


def _publish(event: PredictionEvent) -> None:
    try:
        if _state["producer"] is None:
            from kafka import KafkaProducer

            _state["producer"] = KafkaProducer(bootstrap_servers=settings.kafka_bootstrap)
        _state["producer"].send(TOPIC_PREDICTIONS, event.to_json().encode("utf-8"))
    except Exception as exc:  # noqa: BLE001 — предикт важнее телеметрии
        _state["producer"] = None
        log.warning("publish prediction failed: %s", exc)
