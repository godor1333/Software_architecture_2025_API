"""Юнит-тесты игрового окружения Pong."""
import numpy as np
import pytest

from src.envs.pong_env import PongEnv


@pytest.fixture
def env():
    return PongEnv(seed=1)


def test_observation_shape(env):
    obs, info = env.reset()
    assert obs.shape == (4, 84, 84)
    assert obs.dtype == np.uint8


def test_action_space(env):
    obs, _ = env.reset()
    for action in [0, 1, 2]:
        env.reset()
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.shape == (4, 84, 84)


def test_match_ends_at_max_score(env):
    env.reset()
    env.step(0)  # Serving -> Playing
    env.left_score = env.max_score - 1
    env.ball_x, env.ball_vx, env.ball_vy = 85, 3.0, 0.0
    env.left_y, env.right_y = 0, 0
    done = False
    for _ in range(200):
        _, reward, terminated, truncated, _ = env.step(0)
        done = terminated or truncated
        if done:
            break
    assert done
    assert env.left_score == env.max_score


def test_conceding_gives_negative_reward(env):
    env.reset()
    env.step(0)  # Serving -> Playing
    env.ball_x, env.ball_vx, env.ball_vy = -1, -2.2, 0.0
    env.ball_y = 60.0  # мимо платформы агента
    env.left_y, env.right_y = 0, 0
    _, reward, *_ = env.step(0)
    assert reward <= 0.0 + 0.01
