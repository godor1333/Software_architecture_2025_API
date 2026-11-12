# Паттерн Chain of Responsibility: цепочка обработчиков решения
from common.schemas import ModerationVerdict

class Handler:
    def __init__(self, next_handler=None):
        self._next = next_handler

    def handle(self, ctx):
        handled = self._handle(ctx)
        if handled is not None:
            return handled
        if self._next is not None:
            return self._next.handle(ctx)
        return None

    def _handle(self, ctx):
        raise NotImplementedError


class HardBanHandler(Handler):
    # Явные тяжёлые категории с высокой уверенностью — мгновенный reject
    def _handle(self, ctx):
        p = ctx["policy"].thresholds()
        vcat, vscore = ctx["vision_cat"], ctx["vision_score"]
        if vcat in ("violence", "weapons", "drugs") and vscore >= p[vcat] + 0.15:
            ctx["verdict"].decision = "reject"
            ctx["verdict"].category = vcat
            ctx["verdict"].reasons.append("hard_ban:%s:%.2f" % (vcat, vscore))
            ctx["verdict"].trace.append("HardBanHandler")
            return ctx["verdict"]
        return None


class DuplicateHandler(Handler):
    # Дубликат изображения — спам, reject
    def _handle(self, ctx):
        if ctx["duplicate"]:
            ctx["verdict"].decision = "reject"
            ctx["verdict"].category = "spam"
            ctx["verdict"].reasons.append("duplicate_of:%s" % ctx["duplicate_of"])
            ctx["verdict"].trace.append("DuplicateHandler")
            return ctx["verdict"]
        return None


class CrossModalHandler(Handler):
    # Совпадение сигналов vision и text усиливает оценку (fusion boost)
    def _handle(self, ctx):
        boost = ctx["policy"].fusion_boost(ctx["vision_cat"], ctx["text_cat"])
        ctx["boost"] = boost
        if boost > 0:
            ctx["verdict"].reasons.append(
                "cross_modal_boost:+%.2f (%s+%s)" % (boost, ctx["vision_cat"], ctx["text_cat"]))
        ctx["verdict"].trace.append("CrossModalHandler")
        return None


class ThresholdHandler(Handler):
    # Пороговое решение по стратегии
    def _handle(self, ctx):
        p = ctx["policy"].thresholds()
        vcat, vscore = ctx["vision_cat"], ctx["vision_score"]
        tcat, tscore = ctx["text_cat"], ctx["text_score"]
        eff = vscore + ctx.get("boost", 0.0)
        if vcat != "benign" and eff >= p[vcat]:
            ctx["verdict"].decision = "reject" if vscore >= p[vcat] + 0.10 else "flag"
            ctx["verdict"].category = vcat
            ctx["verdict"].reasons.append("vision:%s:eff=%.2f thr=%.2f" % (vcat, eff, p[vcat]))
            ctx["verdict"].trace.append("ThresholdHandler")
            return ctx["verdict"]
        if tcat == "abuse" and tscore >= 0.70:
            ctx["verdict"].decision = "flag"
            ctx["verdict"].category = "abuse"
            ctx["verdict"].reasons.append("text_abuse:%.2f" % tscore)
            ctx["verdict"].trace.append("ThresholdHandler")
            return ctx["verdict"]
        if tcat == "scam_text" and tscore >= 0.70:
            ctx["verdict"].decision = "flag"
            ctx["verdict"].category = "scam"
            ctx["verdict"].reasons.append("text_scam:%.2f" % tscore)
            ctx["verdict"].trace.append("ThresholdHandler")
            return ctx["verdict"]
        return None


class FinalHandler(Handler):
    def _handle(self, ctx):
        ctx["verdict"].decision = "approve"
        ctx["verdict"].category = "benign" if ctx["vision_cat"] == "benign" else ctx["vision_cat"]
        ctx["verdict"].reasons.append("default_pass")
        ctx["verdict"].trace.append("FinalHandler")
        return ctx["verdict"]


def build_chain():
    # Порядок важен: от самого строгого к дефолтному
    return HardBanHandler(
        DuplicateHandler(
            CrossModalHandler(
                ThresholdHandler(FinalHandler()))))
