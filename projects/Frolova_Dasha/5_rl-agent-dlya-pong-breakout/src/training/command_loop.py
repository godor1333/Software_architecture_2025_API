"""Daemon-режим тренера: паттерн Command поверх Kafka.

Слушает топик training.commands и выполняет команды train/evaluate.
"""
import logging
import uuid

from kafka import KafkaConsumer

from src.agents.factory import AgentFactory
from src.common.config import settings
from src.common.log import setup
from src.common.schemas import GROUP_TRAINER_CMD, TOPIC_COMMANDS
from src.envs.factory import EnvFactory

log = setup()


class TrainingCommandError(Exception):
    pass


class BaseCommandHandler:
    def execute(self, params: dict) -> dict:
        raise NotImplementedError


class TrainCommandHandler(BaseCommandHandler):
    def execute(self, params: dict) -> dict:
        from src.training.train import run_training

        return run_training(
            algorithm=params.get("algorithm", settings.algorithm),
            timesteps=int(params.get("timesteps", settings.total_timesteps)),
        )


class EvaluateCommandHandler(BaseCommandHandler):
    def execute(self, params: dict) -> dict:
        n_episodes = int(params.get("episodes", 10))
        env = EnvFactory.create(settings.env_name, seed=int(params.get("seed", 7)))
        agent = AgentFactory.load(params.get("algorithm", settings.algorithm), settings.model_path)
        totals = []
        for _ in range(n_episodes):
            obs, _info = env.reset()
            done, total = False, 0.0
            while not done:
                action, _ = agent.predict(obs)
                obs, r, term, trunc, _info = env.step(int(action))
                total += float(r)
                done = term or trunc
            totals.append(total)
        result = {"episodes": n_episodes, "mean_reward": sum(totals) / len(totals)}
        log.info("[EVALUATE] %s", result)
        return result


COMMAND_HANDLERS = {
    "train": TrainCommandHandler(),
    "evaluate": EvaluateCommandHandler(),
}


def main() -> None:
    consumer = KafkaConsumer(
        TOPIC_COMMANDS,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=GROUP_TRAINER_CMD,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: v.decode("utf-8"),
    )
    log.info("command loop started, topic=%s", TOPIC_COMMANDS)
    for msg in consumer:
        import json

        try:
            payload = json.loads(msg.value)
            command = payload["command"]
            handler = COMMAND_HANDLERS.get(command)
            if handler is None:
                log.warning("unknown command: %s", command)
                continue
            log.info("[COMMAND] %s params=%s", command, payload.get("params"))
            result = handler.execute(payload.get("params", {}))
            log.info("[COMMAND OK] %s -> %s", command, result)
        except Exception as exc:  # noqa: BLE001
            log.exception("command failed: %s", exc)


if __name__ == "__main__":
    main()
