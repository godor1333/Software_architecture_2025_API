import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.schemas import ModerationVerdict, VISION_CATEGORIES, DECISIONS

def test_verdict_serializes():
    v = ModerationVerdict(post_id="x", decision="flag", category="gambling")
    d = v.to_dict()
    assert d["post_id"] == "x" and d["category"] == "gambling"

def test_no_sexual_categories():
    banned = ("sexual", "nsfw", "nude", "porn", "erotic", " suggestive")
    joined = " ".join(VISION_CATEGORIES).lower()
    assert not any(b in joined for b in banned)
