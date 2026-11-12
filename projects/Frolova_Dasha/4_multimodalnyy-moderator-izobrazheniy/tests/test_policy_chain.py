import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.schemas import ModerationVerdict
from services.fusion.policies import get_policy
from services.fusion.chain import build_chain


def run(policy_name, vision_cat, vision_score, text_cat="clean", text_score=0.0,
        duplicate=False, duplicate_of=None):
    policy = get_policy(policy_name)
    v = ModerationVerdict(post_id="p1", decision="approve", policy=policy.name)
    ctx = {"verdict": v, "policy": policy,
           "vision_cat": vision_cat, "vision_score": vision_score,
           "text_cat": text_cat, "text_score": text_score,
           "duplicate": duplicate, "duplicate_of": duplicate_of}
    build_chain().handle(ctx)
    return v


def test_hard_ban_violence_reject():
    v = run("standard", "violence", 0.95)
    assert v.decision == "reject" and v.category == "violence"

def test_hard_ban_weapons_reject():
    v = run("standard", "weapons", 0.90)
    assert v.decision == "reject"

def test_hard_ban_drugs_reject():
    v = run("standard", "drugs", 0.88)
    assert v.decision == "reject"

def test_duplicate_reject_spam():
    v = run("standard", "benign", 0.9, duplicate=True, duplicate_of="p0")
    assert v.decision == "reject" and v.category == "spam"

def test_cross_modal_boost_triggers_flag():
    v = run("standard", "gambling", 0.55, "scam_text", 0.9)
    assert v.decision in ("flag", "reject")
    assert any("cross_modal_boost" in r for r in v.reasons)

def test_standard_gambling_below_threshold_approves():
    v = run("standard", "gambling", 0.40)
    assert v.decision == "approve"

def test_strict_policy_flags_gambling():
    v = run("strict_family", "gambling", 0.50)
    assert v.decision in ("flag", "reject")

def test_spam_focus_catches_spam():
    v = run("spam_focus", "spam", 0.55)
    assert v.decision in ("flag", "reject")

def test_text_abuse_flags():
    v = run("standard", "benign", 0.9, "abuse", 0.9)
    assert v.decision == "flag" and v.category == "abuse"

def test_text_scam_flags():
    v = run("standard", "benign", 0.9, "scam_text", 0.85)
    assert v.decision == "flag" and v.category == "scam"

def test_benign_approved():
    v = run("standard", "benign", 0.92)
    assert v.decision == "approve"

def test_threshold_not_hardban():
    # violence чуть выше порога, но ниже hard ban порога
    v = run("standard", "violence", 0.72)
    assert v.decision == "flag"

def test_spam_focus_not_overreacting_benign():
    v = run("spam_focus", "benign", 0.9)
    assert v.decision == "approve"

def test_observers_count():
    from services.fusion.observers import MetricsObserver
    m = MetricsObserver()
    class Fake:
        decision = "reject"
        def to_dict(self): return {}
    m.on_verdict(Fake())
    assert m.counts["reject"] == 1

def test_policies_are_distinct_strategies():
    a, b, c = get_policy("standard"), get_policy("strict_family"), get_policy("spam_focus")
    assert a.thresholds()["gambling"] != b.thresholds()["gambling"] != c.thresholds()["gambling"]

def test_chain_trace_filled():
    v = run("standard", "benign", 0.95)
    assert "FinalHandler" in v.trace
