"""Точка входа тренера: one-shot запуск обучения.

Пример: python -m src.training.train --algorithm DQN --timesteps 200000
"""
import argparse
import uuid

from src.agents.factory import AgentFactory
from src.common.config import settings
from src.common.log import setup
from src.envs.factory import EnvFactory
from src.envs.rewards import REWARD_STRATEGIES
from src.training.observers import (
    ConsoleObserver,
    EpisodeObserverWrapper,
    KafkaObserver,
    MLflowObserver,
    TrainerSubject,
)

log = setup()


def build_subject(run_id: str) -> TrainerSubject:
    subject = TrainerSubject()
    subject.attach(ConsoleObserver())
    if not settings.disable_kafka:
        subject.attach(KafkaObserver(settings.kafka_bootstrap))
    if not settings.disable_mlflow:
        subject.attach(
            MLflowObserver(
                experiment_id=f"{settings.algorithm.lower()}-{settings.env_name}",
                run_id=run_id,
                params={
                    "algorithm": settings.algorithm,
                    "env": settings.env_name,
                    "reward_strategy": settings.reward_strategy,
                    "timesteps": settings.total_timesteps,
                    "seed": settings.seed,
                },
            )
        )
    return subject


def run_training(algorithm: str, timesteps: int, max_episodes: int = 10 ** 9) -> dict:
    run_id = uuid.uuid4().hex[:8]
    experiment_id = f"{algorithm.lower()}-{settings.env_name}"
    log.info("start training: exp=%s run=%s", experiment_id, run_id)

    reward_cls = REWARD_STRATEGIES[settings.reward_strategy]
    env = EnvFactory.create(settings.env_name, reward_strategy=reward_cls(), seed=settings.seed)
    subject = build_subject(run_id)
    env = EpisodeObserverWrapper(env, subject, experiment_id, run_id)

    agent = AgentFactory.create(algorithm, env)
    env.model = agent.model

    from stable_baselines3.common.callbacks import StopTrainingOnMaxEpisodes

    stop_cb = StopTrainingOnMaxEpisodes(max_episodes=max_episodes, verbose=0)

    agent.learn(total_timesteps=timesteps, callback=stop_cb)
    agent.save(settings.model_path)

    summary = {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "timesteps": timesteps,
        "model_path": settings.model_path,
    }
    subject.notify_train_end(summary)
    subject.flush()
    log.info("training done: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Pong RL trainer")
    parser.add_argument("--algorithm", default=settings.algorithm)
    parser.add_argument("--timesteps", type=int, default=settings.total_timesteps)
    parser.add_argument("--max-episodes", type=int, default=settings.max_episodes)
    args = parser.parse_args()
    run_training(args.algorithm, args.timesteps, args.max_episodes)


if __name__ == "__main__":
    main()
