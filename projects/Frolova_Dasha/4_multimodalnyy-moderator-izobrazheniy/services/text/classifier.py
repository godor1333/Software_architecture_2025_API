# Паттерн Adapter: порт TextClassifier + toxic-bert и лексикон-фолбэк
import re

ABUSE_WORDS = ["идиот", "дурак", "тупой", "ненавижу", "урод", "упорот", "кретин"]
SCAM_WORDS = ["выиграй", "выигрыш", "приз", "джекпот", "ставк", "казино", "бесплатно",
              "заработок", "крупная сумма", "розыгрыш", "тотализатор", "фрибет"]

class TextClassifier:  # Порт
    def predict(self, text):
        raise NotImplementedError

class ToxicBert(TextClassifier):
    def __init__(self, model_name="unitary/toxic-bert"):
        from transformers import pipeline
        self.pipe = pipeline("text-classification", model=model_name)

    def predict(self, text):
        res = self.pipe(text[:512])[0]
        score = float(res["score"])
        label = res["label"].lower()
        if "toxic" in label or "insult" in label or "obscene" in label:
            cat = "abuse" if score >= 0.6 else "clean"
        else:
            cat = "clean"
        return cat, score

class LexiconFallback(TextClassifier):
    def predict(self, text):
        low = text.lower()
        abuse_hits = sum(1 for w in ABUSE_WORDS if w in low)
        scam_hits = sum(1 for w in SCAM_WORDS if w in low)
        if scam_hits >= 1:
            return "scam_text", min(0.55 + 0.15 * scam_hits, 0.98)
        if abuse_hits >= 1:
            return "abuse", min(0.55 + 0.15 * abuse_hits, 0.98)
        return "clean", 0.9

def make_classifier():
    import os
    backend = os.getenv("TEXT_BACKEND", "bert")
    if backend == "bert":
        try:
            return ToxicBert()
        except Exception as e:
            print("[text] BERT недоступен (%s), лексикон-фолбэк" % e)
    return LexiconFallback()
