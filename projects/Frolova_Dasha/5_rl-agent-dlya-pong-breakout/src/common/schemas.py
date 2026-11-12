"""Схемы сообщений Kafka и общие константы топиков."""
import json
import time
import uuid
from dataclasses import asdict, dataclass, field

# --- топики ----------------------------------------------------------------
TOPIC_EPISODES = "training.episodes"
TOPIC_CHECKPOINTS = "training.checkpoints"
TOPIC_PREDICTIONS = "inference.predictions"
TOPIC_COMMANDS = "training.commands"

# --- consumer groups -------------------------------------------------------
GROUP_METRICS = "metrics-consumer-group"
GROUP_TRAINER_CMD = "trainer-command-group"


@dataclass
class EpisodeMetrics:
    experiment_id: str
    run_id: str
    episode: int
    steps: int
    reward: float
    epsilon: float
    loss: float
    ts: float

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(raw: str) -> "EpisodeMetrics":
        return EpisodeMetrics(**json.loads(raw))


@dataclass
class CheckpointEvent:
    experiment_id: str
    run_id: str
    step: int
    artifact_uri: str
    ts: float

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(raw: str) -> "CheckpointEvent":
        return CheckpointEvent(**json.loads(raw))


@dataclass
class PredictionEvent:
    request_id: str
    model_name: str
    action: int
    action_name: str
    latency_ms: float
    ts: float

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(raw: str) -> "PredictionEvent":
        return PredictionEvent(**json.loads(raw))


@dataclass
class TrainingCommand:
    command: str
    params: dict = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(raw: str) -> "TrainingCommand":
        return TrainingCommand(**json.loads(raw))


ACTION_NAMES = {0: "stay", 1: "up", 2: "down"}
