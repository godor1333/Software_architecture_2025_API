# Паттерн Observer: событие вердикта рассылается подписчикам
import datetime


class VerdictObserver:
    def on_verdict(self, verdict):
        raise NotImplementedError


class MetricsObserver(VerdictObserver):
    def __init__(self):
        self.counts = {"approve": 0, "flag": 0, "reject": 0}

    def on_verdict(self, verdict):
        self.counts[verdict.decision] = self.counts.get(verdict.decision, 0) + 1


class AuditLogObserver(VerdictObserver):
    def on_verdict(self, verdict):
        line = "%s AUDIT post=%s decision=%s category=%s" % (
            datetime.datetime.now().isoformat(), verdict.post_id,
            verdict.decision, verdict.category)
        print(line, flush=True)


class WebhookObserver(VerdictObserver):
    # Доставка внешних событий (в тестах подменяется через Adapter)
    def __init__(self, url=None):
        self.url = url

    def on_verdict(self, verdict):
        if not self.url:
            return
        try:
            import requests
            requests.post(self.url, json=verdict.to_dict(), timeout=2)
        except Exception as e:
            print("[fusion] webhook failed: %s" % e)
