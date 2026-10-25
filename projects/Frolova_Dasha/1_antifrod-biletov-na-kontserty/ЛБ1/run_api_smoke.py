from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE_URL = "http://127.0.0.1:8011"
sys.stdout.reconfigure(encoding="utf-8", errors="strict")


def request_json(path: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8011"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        health = None
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            try:
                health = request_json("/health")
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.4)
        if health is None:
            raise RuntimeError("API did not start within 25 seconds")
        payload = {
            "order_id": "ord-live-001",
            "account_id": "acc-live",
            "device_id": "dev-live",
            "event_id": "concert-42",
            "ticket_count": 6,
            "amount": 42000,
            "purchase_attempts_10m": 5,
            "account_age_days": 1,
            "device_accounts_24h": 3,
        }
        result = request_json("/api/v1/orders/score", method="POST", body=payload)
        retrieved = request_json("/api/v1/orders/ord-live-001")
        print("HEALTH", json.dumps(health, ensure_ascii=False))
        print("POST_SCORE", json.dumps(result, ensure_ascii=False))
        print("GET_SCORE", json.dumps(retrieved, ensure_ascii=False))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()
