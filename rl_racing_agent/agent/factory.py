<<<<<<< HEAD
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.base_class import BaseAlgorithm


class AgentFactory:
    _registry = {
        "ppo": PPO,
        "sac": SAC,
    }

    @classmethod
    def create(cls, algo_name: str, env, **kwargs) -> BaseAlgorithm:
        if algo_name not in cls._registry:
            raise ValueError(f"Unknown algorithm: {algo_name}")
        return cls._registry[algo_name]("MlpPolicy", env, verbose=1, **kwargs)

    @classmethod
    def load(cls, algo_name: str, path: str) -> BaseAlgorithm:
=======
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.base_class import BaseAlgorithm


class AgentFactory:
    _registry = {
        "ppo": PPO,
        "sac": SAC,
    }

    @classmethod
    def create(cls, algo_name: str, env, **kwargs) -> BaseAlgorithm:
        if algo_name not in cls._registry:
            raise ValueError(f"Unknown algorithm: {algo_name}")
        return cls._registry[algo_name]("MlpPolicy", env, verbose=1, **kwargs)

    @classmethod
    def load(cls, algo_name: str, path: str) -> BaseAlgorithm:
>>>>>>> 0037982a52b70d8ed1ac0df57ec0f7ee8fcf872b
        return cls._registry[algo_name].load(path)