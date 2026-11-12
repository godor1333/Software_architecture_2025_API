"""Конфигурация сервисов через переменные окружения."""
import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    kafka_bootstrap: str = _env("KAFKA_BOOTSTRAP", "kafka:9092")
    mlflow_tracking_uri: str = _env("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    postgres_dsn: str = _env(
        "POSTGRES_DSN", "postgresql://pong:pong@postgres:5432/pong_metrics"
    )
    model_path: str = _env("MODEL_PATH", "/models/pong_dqn.zip")
    total_timesteps: int = int(_env("TOTAL_TIMESTEPS", "200000"))
    algorithm: str = _env("ALGORITHM", "DQN")
    env_name: str = _env("ENV_NAME", "PongPygame-v0")
    reward_strategy: str = _env("REWARD_STRATEGY", "shaped")
    seed: int = int(_env("SEED", "42"))
    disable_kafka: bool = _env("DISABLE_KAFKA", "0") == "1"
    disable_mlflow: bool = _env("DISABLE_MLFLOW", "0") == "1"
    max_episodes: int = int(_env("MAX_EPISODES", "500"))


settings = Settings()
