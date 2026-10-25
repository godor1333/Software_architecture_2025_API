import time
import random
import uuid
from ..models import ClickEvent
from ..api.main import evaluate_click_pipeline, repository

def run_simulation(n_events: int = 50, delay_sec: float = 0.02):
    print("=" * 65)
    print(f"  Запуск симуляции стрима кликов ({n_events} событий)")
    print("=" * 65)

    legit_ips = ["178.62.204.10", "85.140.2.45", "94.25.170.12", "213.87.160.8"]
    fraud_ips = ["198.51.100.24", "45.142.122.9", "185.220.101.5", "104.244.76.13"]

    user_agents_legit = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1"
    ]
    user_agents_bot = [
        "python-requests/2.31.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/119.0.6045.105 Safari/537.36",
        "curl/7.88.1"
    ]

    for i in range(1, n_events + 1):
        is_bot = random.random() < 0.25

        if is_bot:
            bot_kind = random.choice(["blacklist", "headless", "fast_clicker"])
            if bot_kind == "blacklist":
                ip = "198.51.100.24"
                ua = random.choice(user_agents_legit)
                interval = random.randint(150, 600)
            elif bot_kind == "headless":
                ip = random.choice(fraud_ips)
                ua = random.choice(user_agents_bot)
                interval = random.randint(30, 200)
            else:
                ip = random.choice(fraud_ips)
                ua = random.choice(user_agents_legit)
                interval = random.randint(20, 120)
        else:
            ip = random.choice(legit_ips)
            ua = random.choice(user_agents_legit)
            interval = random.randint(1200, 6000)

        ev = ClickEvent(
            click_id=str(uuid.uuid4())[:8],
            publisher_id=f"pub_{random.randint(101, 105)}",
            campaign_id=f"cmp_{random.randint(1, 3)}",
            user_id=f"usr_{random.randint(1000, 9999)}",
            ip_address=ip,
            user_agent=ua,
            url="https://shop.example.com/item/42",
            click_interval_ms=interval,
            device_type="mobile" if "iPhone" in ua else "desktop",
            os="iOS" if "iPhone" in ua else "Windows"
        )

        res = evaluate_click_pipeline(ev)
        tag = f"[{res.status.value}]"
        print(f"[{i:02d}] {tag:<11} Score: {res.fraud_score:0.2f} | IP: {ip:<14} | Reason: {res.primary_reason[:38]} ({res.processing_time_ms} ms)")

        if delay_sec > 0:
            time.sleep(delay_sec)

    print("\n" + "=" * 65)
    print("  Итоговая аналитическая сводка")
    print("=" * 65)
    metrics = repository.get_metrics()
    print(f"Всего обработано кликов:   {metrics.total_processed}")
    print(f"Выявлено фрода:            {metrics.total_fraud_detected}")
    print(f"Процент фрода:             {metrics.fraud_rate_percentage:.1f}%")
    print(f"Средняя задержка:          {metrics.avg_latency_ms:.2f} ms")
    print(f"Заблокировано правилами:   {metrics.blocked_by_rules_count}")
    print(f"Заблокировано ML:          {metrics.blocked_by_ml_count}")
    print(f"Топ подозрительных IP:     {', '.join(metrics.top_blocked_ips)}")
    print("=" * 65)

if __name__ == "__main__":
    run_simulation(n_events=30, delay_sec=0.01)
