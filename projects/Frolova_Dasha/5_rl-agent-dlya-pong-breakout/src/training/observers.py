"""Паттерн Observer: события тренировки рассылаются наблюдателям.

TrainerSubject владеет списком наблюдателей; каждый наблюдатель
(консоль, MLflow, Kafka) получает события эпизода, чекпоинта и завершения.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import List

import gymnasium as gym

from src.common.config import settings
from src.common.schemas import CheckpointEvent, EpisodeMetrics

log = logging.getLogger("pong.observer")


class TrainingObserver(ABC):
    @abstractmethod
    def on_episode(self, metrics: EpisodeMetrics) -> None:
        raise NotImplementedError

    def on_checkpoint(self, event: CheckpointEvent) -> None:
        pass

    def on_train_end(self, summary: dict) -> None:
        pass


class ConsoleObserver(TrainingObserver):
    def on_episode(self, metrics: EpisodeMetrics) -> None:
        log.info(
            "[EPISODE] exp=%s ep=%d steps=%d reward=%.2f eps=%.2f",
            metrics.experiment_id, metrics.episode, metrics.steps,
            metrics.reward, metrics.epsilon,
        )

    def on_checkpoint(self, event: CheckpointEvent) -> None:
        log.info("[CHECKPOINT] step=%d -> %s", event.step, event.artifact_uri)


class KafkaObserver(TrainingObserver):
    """Публикует события тренировки в Kafka (best-effort)."""

    def __init__(self, bootstrap: str, topics=None):
        from kafka import KafkaProducer

        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda v: v.encode("utf-8"),
            retries=3,
        )

    def on_episode(self, metrics: EpisodeMetrics) -> None:
        from src.common.schemas import TOPIC_EPISODES

        self._send(TOPIC_EPISODES, metrics.to_json())

    def on_checkpoint(self, event: CheckpointEvent) -> None:
        from src.common.schemas import TOPIC_CHECKPOINTS

        self._send(TOPIC_CHECKPOINTS, event.to_json())

    def _send(self, topic: str, payload: str) -> None:
        try:
            self.producer.send(topic, payload)
        except Exception as exc:  # noqa: BLE001 — Kafka не должна ронять тренировку
            log.warning("kafka send failed (%s): %s", topic, exc)

    def flush(self) -> None:
        try:
            self.producer.flush(timeout=5)
        except Exception as exc:  # noqa: BLE001
            log.warning("kafka flush failed: %s", exc)


class MLflowObserver(TrainingObserver):
    """Логирует метрики и артефакты в MLflow."""

    def __init__(self, experiment_id: str, run_id: str, params: dict = None):
        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment("pong-rl")
        self._mlflow = mlflow
        mlflow.start_run(run_name=f"{experiment_id}-{run_id}")
        mlflow.log_params(params or {})

    def on_episode(self, metrics: EpisodeMetrics) -> None:
        self._mlflow.log_metrics(
            {
                "episode_reward": metrics.reward,
                "episode_steps": metrics.steps,
                "epsilon": metrics.epsilon,
            },
            step=metrics.episode,
        )

    def on_train_end(self, summary: dict) -> None:
        self._mlflow.log_metrics(
            {k: v for k, v in summary.items() if isinstance(v, (int, float))}
        )
        self._mlflow.end_run()


class TrainerSubject:
    """Субъект паттерна Observer."""

    def __init__(self) -> None:
        self._observers: List[TrainingObserver] = []

    def attach(self, observer: TrainingObserver) -> None:
        self._observers.append(observer)

    def notify_episode(self, metrics: EpisodeMetrics) -> None:
        for obs in self._observers:
            try:
                obs.on_episode(metrics)
            except Exception as exc:  # noqa: BLE001
                log.warning("observer %s failed: %s", type(obs).__name__, exc)

    def notify_checkpoint(self, event: CheckpointEvent) -> None:
        for obs in self._observers:
            try:
                obs.on_checkpoint(event)
            except Exception as exc:  # noqa: BLE001
                log.warning("observer %s failed: %s", type(obs).__name__, exc)

    def notify_train_end(self, summary: dict) -> None:
        for obs in self._observers:
            try:
                obs.on_train_end(summary)
            except Exception as exc:  # noqa: BLE001
                log.warning("observer %s failed: %s", type(obs).__name__, exc)

    def flush(self) -> None:
        for obs in self._observers:
            if isinstance(obs, KafkaObserver):
                obs.flush()


class EpisodeObserverWrapper(gym.Wrapper):
    """Считает эпизоды и рассылает EpisodeMetrics всем наблюдателям."""

    def __init__(self, env, subject: TrainerSubject, experiment_id: str, run_id: str):
        super().__init__(env)
        self.subject = subject
        self.experiment_id = experiment_id
        self.run_id = run_id
        self._episode = 0
        self._episode_reward = 0.0
        self._episode_len = 0
        self.model = None


    def reset(self, **kwargs):
        self._episode += 1
        self._episode_reward = 0.0
        self._episode_len = 0
        return super().reset(**kwargs)

    def step(self, action):
        obs, reward, terminated, truncated, info = super().step(action)
        self._episode_reward += float(reward)
        self._episode_len += 1
        if terminated or truncated:
            self.subject.notify_episode(
                EpisodeMetrics(
                    experiment_id=self.experiment_id,
                    run_id=self.run_id,
                    episode=self._episode,
                    steps=self._episode_len,
                    reward=self._episode_reward,
                    epsilon=float(getattr(self.model, "exploration_rate", 0.0)),
                    loss=float(info.get("loss", 0.0)),
                    ts=time.time(),
                )
            )
        return obs, reward, terminated, truncated, info
