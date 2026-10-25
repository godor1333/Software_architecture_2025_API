from __future__ import annotations

"""Publish a real order through Docker Compose and wait for the Kafka pipeline result."""

import json
import sys
import time
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"
sys.stdout.reconfigure(encoding="utf-8", errors="strict")


def request_json(path: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
    encoded = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        f"{BASE_URL}{path}", data=encoded, method=method,
        headers={"Content-Type": "application/json"} if encoded else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def main() -> None:
    order_id = f"ord-pipeline-{int(time.time())}"
    payload = {
        "order_id": order_id,
        "account_id": "acc-pipeline",
        "device_id": "dev-pipeline",
        "event_id": "concert-42",
        "ticket_count": 6,
        "amount": 42000,
        "purchase_attempts_10m": 5,
        "account_age_days": 1,
        "device_accounts_24h": 3,
    }
    status, submitted = request_json("/api/v1/orders/score", method="POST", body=payload)
    if status != 201 or submitted.get("status") != "PENDING":
        raise RuntimeError(f"Expected Kafka acknowledgement, got {status}: {submitted}")
    print("PUBLISHED", json.dumps(submitted, ensure_ascii=False))

    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        status, result = request_json(f"/api/v1/orders/{order_id}")
        if status == 200:
            print("DECISION", json.dumps(result, ensure_ascii=False))
            _, dashboard = request_json("/api/v1/dashboard/summary")
            print("DASHBOARD", json.dumps(dashboard, ensure_ascii=False))
            return
        if status != 404:
            raise RuntimeError(f"Unexpected polling response: {status}: {result}")
        time.sleep(1)
    raise TimeoutError("Kafka pipeline did not persist a decision within 40 seconds")


if __name__ == "__main__":
    main()
