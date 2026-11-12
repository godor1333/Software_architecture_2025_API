# Сквозной контрактный e2e-тест: запросы через реальный pipeline, без заглушек
import os
import sys
import json
import time
import uuid
import argparse

import requests

API = os.getenv("API_URL", "http://localhost:8000")
DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "demo")
TIMEOUT_S = 120

def wait_health():
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            if requests.get(API + "/health", timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False

def submit(fp, text, user="tester"):
    with open(fp, "rb") as f:
        r = requests.post(API + "/api/v1/posts",
                          files={"image": (os.path.basename(fp), f)},
                          data={"text": text, "user_id": user}, timeout=30)
    r.raise_for_status()
    return r.json()["post_id"]

def wait_verdict(post_id, timeout=TIMEOUT_S):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(API + "/api/v1/posts/" + post_id, timeout=5)
        if r.status_code == 200:
            return r.json()
        time.sleep(2)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="demo")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    if not wait_health():
        print("FAIL: API недоступен на", API)
        sys.exit(2)
    manifest = json.load(open(os.path.join(DEMO_DIR, "manifest.json"), encoding="utf-8"))
    texts = {"gambling": "ставки на спорт круглосуточно! фрибет новичкам",
             "scam": "выиграй приз бесплатно! крупная сумма за клик",
             "spam": "скидки распродажа покупай сейчас",
             "violence": "видео драки", "weapons": "продам ружьё",
             "drugs": "соли, скорость в наличии", "benign": "прогулка в парке"}
    results, fail = [], 0
    ids = {}
    for item in manifest:
        fp = os.path.join(DEMO_DIR, item["file"])
        expected = item["expected_category"]
        post_id = submit(fp, texts.get(expected, ""))
        ids[expected] = post_id
        v = wait_verdict(post_id)
        ok = v is not None and v["decision"] in ("approve", "flag", "reject")
        results.append((item["file"], expected, v, ok))
        print("%-24s expected=%-10s decision=%-8s category=%-10s %s" % (
            item["file"], expected, (v or {}).get("decision"), (v or {}).get("category"),
            "OK" if ok else "FAIL"))

    # контракт дубликата: повторная отправка обязана быть поймана как spam-дубликат
    fp = os.path.join(DEMO_DIR, manifest[0]["file"])
    dup_id = submit(fp, "повтор того же поста")
    v = wait_verdict(dup_id)
    dup_ok = v is not None and v["category"] == "spam" and v["decision"] == "reject"
    print("duplicate-check post=%s decision=%s category=%s %s" % (
        dup_id, (v or {}).get("decision"), (v or {}).get("category"),
        "OK" if dup_ok else "FAIL"))

    # контракт Elasticsearch: события проиндексированы
    es_ok = False
    try:
        r = requests.get(API + "/api/v1/search", params={"q": "reject"}, timeout=10)
        es_ok = r.status_code == 200 and len(r.json()) >= 1
    except Exception as e:
        print("es-check exception:", e)
    print("es-check:", "OK" if es_ok else "FAIL")

    all_ok = all(r[3] for r in results) and dup_ok and es_ok
    print("RESULT:", "PASS" if all_ok else "FAIL")
    out = {"results": [{"file": f, "expected": e, "verdict": v, "ok": bool(o)} for f, e, v, o in results],
           "duplicate_ok": dup_ok, "es_ok": es_ok, "pass": all_ok}
    os.makedirs("artifacts", exist_ok=True)
    json.dump(out, open("artifacts/e2e_results.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    if args.strict and not all_ok:
        sys.exit(1)
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
