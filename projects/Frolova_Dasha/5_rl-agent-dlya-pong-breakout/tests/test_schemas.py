"""Тесты схем сообщений Kafka."""
import json

from src.common.schemas import (
    CheckpointEvent,
    EpisodeMetrics,
    PredictionEvent,
    TrainingCommand,
)


def test_episode_roundtrip():
    m = EpisodeMetrics("exp", "run", 1, 10, 0.5, 1.0, 0.2, 1.0)
    m2 = EpisodeMetrics.from_json(m.to_json())
    assert m2 == m


def test_checkpoint_roundtrip():
    e = CheckpointEvent("exp", "run", 1000, "file:///models/x.zip", 1.0)
    assert CheckpointEvent.from_json(e.to_json()) == e


def test_prediction_roundtrip():
    p = PredictionEvent("req1", "DQN", 2, "down", 1.5, 1.0)
    assert PredictionEvent.from_json(p.to_json()) == p


def test_command_roundtrip():
    c = TrainingCommand("train", {"timesteps": 1000})
    assert TrainingCommand.from_json(c.to_json()) == c
    assert isinstance(json.loads(c.to_json())["params"], dict)
