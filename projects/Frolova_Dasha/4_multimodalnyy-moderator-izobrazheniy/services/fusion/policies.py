THRESHOLDS_STANDARD = {
    "violence": 0.30, "weapons": 0.30, "drugs": 0.30,
    "gambling": 0.30, "scam": 0.30, "spam": 0.30, "benign": 1.01,
}
THRESHOLDS_STRICT = {
    "violence": 0.26, "weapons": 0.26, "drugs": 0.26,
    "gambling": 0.26, "scam": 0.26, "spam": 0.26, "benign": 1.01,
}
THRESHOLDS_SPAM_FOCUS = {
    "violence": 0.35, "weapons": 0.35, "drugs": 0.35,
    "gambling": 0.35, "scam": 0.35, "spam": 0.25, "benign": 1.01,
}


class ModerationPolicy:  
    name = "standard"

    def thresholds(self):
        raise NotImplementedError

    def fusion_boost(self, vcat, tcat):
        # усиление сигнала при совпадении модальностей
        return 0.0

class StandardPolicy(ModerationPolicy):
    name = "standard"

    def thresholds(self):
        return THRESHOLDS_STANDARD

    def fusion_boost(self, vcat, tcat):
        pairs = {("gambling", "scam_text"), ("scam", "scam_text"), ("spam", "scam_text"),
                 ("violence", "abuse"), ("weapons", "abuse"), ("drugs", "abuse")}
        return 0.10 if (vcat, tcat) in pairs else 0.0

class StrictFamilyPolicy(ModerationPolicy):
    # Для разделов с детьми: жёсткие пороги, абьюз в тексте запрещён всегда
    name = "strict_family"

    def thresholds(self):
        return THRESHOLDS_STRICT

    def fusion_boost(self, vcat, tcat):
        return 0.15 if tcat == "abuse" else 0.10

class SpamFocusPolicy(ModerationPolicy):
    # Для пикового спама: ловим спам агрессивнее, остальное мягче
    name = "spam_focus"

    def thresholds(self):
        return THRESHOLDS_SPAM_FOCUS

    def fusion_boost(self, vcat, tcat):
        return 0.10 if tcat == "scam_text" else 0.0

POLICIES = {
    "standard": StandardPolicy,
    "strict_family": StrictFamilyPolicy,
    "spam_focus": SpamFocusPolicy,
}

def get_policy(name):
    return POLICIES.get(name, StandardPolicy)()
