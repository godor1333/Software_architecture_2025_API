"""Оценка обученного агента: те же условия среды, что в тренировке."""
import argparse
import json
import os

import numpy as np

from src.agents.factory import AgentFactory
from src.common.config import settings
from src.envs.factory import EnvFactory
from src.envs.rewards import REWARD_STRATEGIES


def main() -> None:
    parser = argparse.ArgumentParser(description="Pong RL evaluate")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--model", default=settings.model_path)
    args = parser.parse_args()

    algorithm = "DQN"
    meta_path = args.model + ".meta.json"
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            algorithm = json.load(f)["algorithm"]

    model = AgentFactory.load(algorithm, args.model)

    reward_cls = REWARD_STRATEGIES[settings.reward_strategy]
    env = EnvFactory.create(
        settings.env_name,
        reward_strategy=reward_cls(),
        seed=settings.seed,
    )
    print(f"strategy={settings.reward_strategy} seed={settings.seed}")

    rewards, steps_list = [], []
    for ep in range(1, args.episodes + 1):
        obs, _info = env.reset()
        done, total, steps = False, 0.0, 0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _info = env.step(int(action))
            total += float(reward)
            steps += 1
            done = terminated or truncated
        rewards.append(total)
        steps_list.append(steps)
        print(f"ep={ep} steps={steps} reward={total:.2f}", flush=True)

    print(
        f"avg_reward={np.mean(rewards):.2f} "
        f"min={min(rewards):.2f} max={max(rewards):.2f}"
    )
    env.close()


if __name__ == "__main__":
    main()
