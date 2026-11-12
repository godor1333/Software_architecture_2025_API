"""Smoke-тест всего pipeline: health + реальные запросы к API + чтение метрик.

Запуск: docker compose run --rm smoke
"""
import json
import os
import time

import requests

INFERENCE_URL = os.getenv("INFERENCE_URL", "http://inference:8000")
METRICS_URL = os.getenv("METRICS_URL", "http://metrics-api:8001")


def check(name: str, ok: bool, details: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name} {details}")
    return ok


def wait_for(url: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=3).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


def main() -> None:
    ok = True

    # 1. health inference
    r = requests.get(f"{INFERENCE_URL}/health", timeout=5)
    ok &= check("GET /health (inference)", r.status_code == 200, r.text[:120])

    # 2. predict: если модель обучена — 200, иначе ожидаем честный 503
    obs = [[[0] * 84 for _ in range(84)] for _ in range(4)]
    r = requests.post(
        f"{INFERENCE_URL}/predict", json={"observation": obs}, timeout=10
    )
    if r.status_code == 200:
        body = r.json()
        ok &= check(
            "POST /predict", True,
            f'action={body["action"]} latency={body["latency_ms"]}ms',
        )
    elif r.status_code == 503:
        ok &= check("POST /predict", True, "503 — модель ещё не обучена (ожидаемо до тренера)")
    else:
        ok &= check("POST /predict", False, f"status={r.status_code}")

    # 3. health metrics api
    r = requests.get(f"{METRICS_URL}/health", timeout=5)
    ok &= check("GET /health (metrics-api)", r.status_code == 200, r.text[:120])

    # 4. метрики экспериментов (может быть пусто до первого обучения)
    r = requests.get(f"{METRICS_URL}/experiments", timeout=5)
    ok &= check("GET /experiments", r.status_code == 200, r.text[:200])

    print("=" * 60)
    print("SMOKE RESULT:", "ALL PASS" if ok else "HAS FAILURES")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
