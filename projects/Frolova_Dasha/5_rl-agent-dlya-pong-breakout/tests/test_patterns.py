"""Тесты паттернов: Factory, Strategy, State, Command."""
import pytest

from src.agents.factory import AgentFactory
from src.envs.commands import ACTION_COMMANDS
from src.envs.factory import EnvFactory
from src.envs.game_states import GameOverState, PlayingState
from src.envs.pong_env import PongEnv
from src.envs.rewards import REWARD_STRATEGIES


def test_env_factory_known_name():
    env = EnvFactory.create("PongPygame-v0", seed=1)
    assert env.observation_space.shape == (4, 84, 84)
    env.close()


def test_env_factory_unknown_name_raises():
    with pytest.raises(ValueError):
        EnvFactory.create("NoSuchEnv-v0")


def test_command_paddle_moves():
    env = PongEnv(seed=1)
    env.reset()
    before = env.left_y
    ACTION_COMMANDS[2].execute(env)  # down
    assert env.left_y == before + env.paddle_speed
    ACTION_COMMANDS[2].execute(env)  # отходим от верхней границы
    ACTION_COMMANDS[1].execute(env)  # up
    ACTION_COMMANDS[1].execute(env)
    assert env.left_y == before


def test_state_transitions():
    env = PongEnv(seed=1)
    env.reset()
    env.step(0)  # Serving -> Playing
    assert isinstance(env._state, PlayingState)
    env.right_score = env.max_score
    env.ball_x, env.ball_vx, env.ball_vy = -1, -2.2, 0.0
    env.ball_y = 60.0
    env.left_y, env.right_y = 0, 0
    _, _, terminated, *_ = env.step(0)
    assert terminated
    assert isinstance(env._state, GameOverState)


def test_reward_strategies_registered():
    assert set(REWARD_STRATEGIES) == {"sparse", "shaped"}


def test_agent_factory_unknown_raises():
    with pytest.raises(ValueError):
        AgentFactory.create("NOT_AN_ALGO", env=None)


def test_agent_factory_registry_has_dqn_and_ppo():
    import src.training.strategies  # noqa: F401
    assert {"DQN", "PPO"} <= set(AgentFactory._registry)
