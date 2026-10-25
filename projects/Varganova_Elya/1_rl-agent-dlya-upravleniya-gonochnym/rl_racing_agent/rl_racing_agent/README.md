# RL Racing Agent

RL-агент для управления гоночным автомобилем (газ/тормоз/руль).
Архитектура: training service + game simulator + telemetry streaming.
Offline training и online inference разделены.

## Стек
Python, Gymnasium, Stable-Baselines3, PyTorch, Pygame,
FastAPI, Kafka, PostgreSQL, Grafana.

## Паттерны
Strategy, State, Observer, Factory, Command, Producer–Consumer.

## Быстрый старт

### 1. Инфраструктура
```bash
docker compose up -d zookeeper kafka postgres grafana