# RL-агент для Pong (DQN) — production-подобная архитектура

Обучение RL-агента игре в Pong и вывод модели в эксплуатацию: обучение отделено
от инференса, события идут через Kafka в PostgreSQL, эксперименты трекаются
в MLflow, работоспособность проверяется сквозным smoke-тестом.

## Архитектура

- `trainer` — обучение DQN (SB3), публикует события в Kafka (`training.episodes`,
  `training.checkpoints`), метрики и артефакты — в MLflow.
- `inference` (FastAPI :8000) — предикт обученной модели; предикты уходят в
  Kafka (`inference.predictions`).
- `metrics-consumer` — транспорт событий Kafka → PostgreSQL.
- `metrics-api` (FastAPI :8001) — чтение и агрегация метрик из БД.
- `mlflow` (UI :5000) — трекинг экспериментов; `postgres` — аналитическое
  хранилище; `kafka` + `zookeeper` — шина событий. Все сервисы в сети `pong-net`.

## Быстрый старт

```bash
docker compose up -d --build        # поднять kafka, postgres, mlflow, inference, metrics-api
docker compose run --rm trainer     # обучение агента (модель появится в volume models-data)
docker compose run --rm smoke       # smoke-тест: реальные HTTP-запросы к API из сети compose
docker compose run --rm trainer pytest -v   # юнит-тесты (pytest)
```

## API

```bash
curl localhost:8000/health
# {"status":"ok","model_loaded":true,"model":"DQN"}

curl -X POST localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"observation": [[[0]*84, [0]*84, [0]*84, [0]*84]]}'

curl localhost:8001/experiments
curl "localhost:8001/summary?experiment_id=dqn-PongPygame-v0"
```

## Результаты

| Показатель | Значение |
|---|---|
| Random baseline | −4.44 |
| DQN: хвост последних 10 эпизодов последнего прогона | +9.92 |
| DQN: жадная политика, 5 эпизодов | +10.08 |
| Improvement (last_50 vs first_50 по `/summary`) | +15.02 |

## Проверка и артефакты

Папка `artifacts/` — доказательная база запуска: логи контейнеров, инспекция
сети, список Kafka-топиков, отчёт pytest (15 passed), вывод smoke-теста
(ALL PASS), схема БД и ряд наград последнего прогона. Подробности — в REPORT.md.
