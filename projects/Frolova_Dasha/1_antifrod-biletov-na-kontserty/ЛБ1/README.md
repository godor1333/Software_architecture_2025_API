# TicketShield — антифрод билетов на концерты

Лабораторная работа №1 по дисциплине «Логика и архитектура вычислительных средств». Проект выявляет массовые покупки, ботов и подозрительные связи аккаунта с устройством при оформлении концертных билетов.

Решение имеет два режима. `local` — быстрый запуск без внешней инфраструктуры для разработки и автоматических тестов. `distributed` — полноценный Docker Compose стенд: API публикует заказ в Kafka, Feature Service обогащает событие счётчиками Redis, Scoring Service принимает решение LightGBM/правилами, сохраняет его в PostgreSQL и выгружает в ClickHouse. Дашборд берёт сводку из ClickHouse.

## Состав

- `app/main.py` — FastAPI, API и HTML-дашборд `/dashboard`;
- `app/workers.py` — Kafka consumer groups `feature-service`, `scoring-service`, `analytics-service`;
- `app/events.py` — UTF-8 JSON producer/consumer Kafka;
- `app/storage.py` — Redis Feature Store, PostgreSQL Repository, ClickHouse Analytics Store и локальные адаптеры;
- `sql/` — самостоятельные DDL-схемы PostgreSQL и ClickHouse с индексами;
- `data/fraud_orders.csv` — воспроизводимый синтетический набор из 2400 событий без ПДн;
- `artifacts/` — LightGBM-модель, метрики и скриншоты реального запуска;
- `tests/` — unit/API/pipeline tests;
- `Отчёт_ЛР1_Антифрод_билетов.docx` — отчёт;
- `Результаты_проверки.md` — подтверждение фактической проверки.

## Архитектура и Kafka

```text
Клиент → FastAPI → orders.created → Feature Service → orders.enriched
                                      │ Redis              │
                                      └── PostgreSQL ← Scoring Service (LightGBM + Rules)
                                                              │
                                                antifraud.decisions → Analytics group
                                                              │
                                                         ClickHouse → /dashboard
```

| Topic | Producer | Consumer group | Формат |
|---|---|---|---|
| `orders.created` | FastAPI | `feature-service` | UTF-8 JSON `OrderEvent` |
| `orders.enriched` | Feature Service | `scoring-service` | UTF-8 JSON `OrderEvent` с признаками Redis |
| `antifraud.decisions` | Scoring Service | `analytics-service` | UTF-8 JSON `ScoreResponse` |

## Быстрый локальный запуск

Требуется Python 3.12+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python serve_api.py
```

Открыть `http://127.0.0.1:8012/docs` или `http://127.0.0.1:8012/dashboard`.

В локальном режиме `POST /api/v1/orders/score` сразу возвращает результат. Используйте, например:

```json
{
  "order_id": "ord-demo-001",
  "account_id": "acc-100",
  "device_id": "dev-77",
  "event_id": "concert-42",
  "ticket_count": 6,
  "amount": 42000,
  "purchase_attempts_10m": 5,
  "account_age_days": 1,
  "device_accounts_24h": 3
}
```

## Полный стенд Docker Compose

```powershell
docker compose up --build -d
python run_distributed_smoke.py
```

После проверки:

```powershell
docker compose logs --tail=100 antifraud-api feature-service scoring-service analytics-service
docker compose down -v
```

Сервисы: API и Swagger — `http://localhost:8000/docs`; dashboard — `http://localhost:8000/dashboard`; Kafka снаружи — `localhost:29092`. В режиме Compose `POST /api/v1/orders/score` возвращает `PENDING`, а скрипт `run_distributed_smoke.py` ждёт результат из PostgreSQL и сводку ClickHouse. Запуск выполняется без облачных сервисов; тестовые логины и пароли заданы только для локального Compose-стенда.

## ML и проверка качества

```powershell
python generate_dataset.py
python train_model.py
```

Данные делятся стратифицированно: 1800 обучающих и 600 тестовых событий. Сравниваются правило-baseline и LightGBM. Метрики, важности признаков, порог `0.15` и ограничения зафиксированы в `artifacts/metrics.json` и отчёте.

## Паттерны

- Chain of Responsibility — последовательно применяет правила скорости, массовой покупки, свежего аккаунта и общего устройства;
- Strategy + Adapter — переключает rule baseline/LightGBM за единым интерфейсом `predict_risk`;
- Repository — `ScoreStore` отделяет сохранение решений от FastAPI; есть PostgreSQL- и in-memory реализации;
- Factory — `build_service()` собирает набор адаптеров для local/distributed окружения;
- Circuit Breaker — для публикации в Kafka: после трёх ошибок API временно возвращает HTTP 503 без повторных обращений к недоступному брокеру; healthchecks Docker не запускают зависимые сервисы до готовности хранилищ.
