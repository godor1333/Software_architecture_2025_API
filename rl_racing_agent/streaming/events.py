from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TelemetryEvent:
    episode: int
    step: int
    reward: float
    speed: float
    progress: float
    crashed: bool
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return asdict(self)