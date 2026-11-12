from dataclasses import dataclass, field, asdict
from typing import Optional

VISION_CATEGORIES = ["violence", "weapons", "drugs", "gambling", "scam", "spam", "benign"]
TEXT_CATEGORIES = ["abuse", "scam_text", "clean"]
DECISIONS = ["approve", "flag", "reject"]

@dataclass
class MediaSubmitted:
    post_id: str
    user_id: str
    media_key: str
    text: str
    created_at: str

    def to_dict(self):
        return asdict(self)

@dataclass
class VisionVerdict:
    post_id: str
    category: str
    score: float
    duplicate: bool = False
    duplicate_of: Optional[str] = None

    def to_dict(self):
        return asdict(self)

@dataclass
class TextVerdict:
    post_id: str
    category: str
    score: float

    def to_dict(self):
        return asdict(self)

@dataclass
class ModerationVerdict:
    post_id: str
    decision: str
    category: str = "none"
    scores: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)
    policy: str = "standard"
    trace: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
