<<<<<<< HEAD
import os
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.env_util import make_vec_env
from simulator.env import RacingEnv
from agent.factory import AgentFactory
from agent.strategy import TimeRewardStrategy
from streaming.producer import TelemetryProducer
from streaming.events import TelemetryEvent


def train(total_timesteps=200_000):
    env = make_vec_env(RacingEnv, n_envs=4)
    model = AgentFactory.create("ppo", env, learning_rate=3e-4, n_steps=2048)

    checkpoint = CheckpointCallback(
        save_freq=10_000,
        save_path="./models/",
        name_prefix="ppo_racing",
    )

    model.learn(total_timesteps=total_timesteps, callback=checkpoint)
    model.save("models/ppo_racing_final")
    env.close()


if __name__ == "__main__":
    os.makedirs("models", exist_ok=True)
=======
import os
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.env_util import make_vec_env
from simulator.env import RacingEnv
from agent.factory import AgentFactory
from agent.strategy import TimeRewardStrategy
from streaming.producer import TelemetryProducer
from streaming.events import TelemetryEvent


def train(total_timesteps=200_000):
    env = make_vec_env(RacingEnv, n_envs=4)
    model = AgentFactory.create("ppo", env, learning_rate=3e-4, n_steps=2048)

    checkpoint = CheckpointCallback(
        save_freq=10_000,
        save_path="./models/",
        name_prefix="ppo_racing",
    )

    model.learn(total_timesteps=total_timesteps, callback=checkpoint)
    model.save("models/ppo_racing_final")
    env.close()


if __name__ == "__main__":
    os.makedirs("models", exist_ok=True)
>>>>>>> 0037982a52b70d8ed1ac0df57ec0f7ee8fcf872b
    train()