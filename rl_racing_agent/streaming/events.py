<<<<<<< HEAD
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
=======
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
>>>>>>> 0037982a52b70d8ed1ac0df57ec0f7ee8fcf872b
        return asdict(self)