# Паттерн Adapter: порт VisionClassifier + CLIP zero-shot и dummy-реализация
import numpy as np
from PIL import Image

PROMPTS = {
    "violence": [
        "a photo of a violent fight between people",
        "graphic violence with blood and injuries",
        "a person being beaten or attacked",
    ],
    "weapons": [
        "a photo of a firearm, a rifle or a pistol",
        "a gun held in a person's hand",
        "a combat knife shown as a weapon",
    ],
    "drugs": [
        "a photo of illegal drugs and narcotics",
        "syringes and pills of illegal substances",
        "drug paraphernalia on a table",
    ],
    "gambling": [
        "casino slot machines and poker chips",
        "a roulette table in a casino",
        "a betting advertisement with odds and stakes",
    ],
    "scam": [
        "a scam banner promising a fake prize or lottery win",
        "a get rich quick scheme advertisement",
        "a fraudulent message asking for money or personal data",
    ],
    "spam": [
        "an advertising banner with bright promotional text",
        "a promotional poster with bold offers and discounts",
        "a marketing flyer with lots of text",
    ],
    "benign": [
        "an ordinary everyday photo without any text",
        "a peaceful landscape photo",
        "a photo of food or a pet",
        "a family photo in a park",
    ],
}

class VisionClassifier:  # Порт
    def predict(self, img: Image.Image):
        raise NotImplementedError

class CLIPZeroShot(VisionClassifier):
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        import torch
        from transformers import CLIPModel, CLIPProcessor
        self.torch = torch
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()
        self._texts = []
        self._labels = []
        for label, prompts in PROMPTS.items():
            for p in prompts:
                self._labels.append(label)
                self._texts.append(p)

    def predict(self, img):
        torch = self.torch
        with torch.no_grad():
            inputs = self.processor(text=self._texts, images=img.convert("RGB"),
                                    return_tensors="pt", padding=True)
            out = self.model(**inputs)
            probs = out.logits_per_image.softmax(dim=1)[0].tolist()
        # усреднение вероятностей промптов внутри класса вместо max:
        # max реагирует на случайное совпадение одного промпта и шумит
        agg = {}
        for label, p in zip(self._labels, probs):
            agg.setdefault(label, []).append(p)
        scores = {label: float(np.mean(v)) for label, v in agg.items()}
        best = max(scores, key=scores.get)
        return best, scores[best], scores

class DummyVision(VisionClassifier):
    # Работает без весов модели, чтобы pipeline можно было проверить офлайн
    def predict(self, img):
        arr = np.asarray(img.convert("RGB").resize((64, 64)), dtype=np.float32)
        mean = arr.mean(axis=(0, 1))
        scores = {c: 0.05 for c in PROMPTS}
        if mean.mean() > 170:  # светлая пёстрая картинка -> похоже на баннер
            scores["spam"] = 0.55
            scores["benign"] = 0.35
        else:
            scores["benign"] = 0.6
        best = max(scores, key=scores.get)
        return best, float(scores[best]), scores

def make_classifier():
    import os
    backend = os.getenv("VISION_BACKEND", "clip")
    if backend == "clip":
        try:
            return CLIPZeroShot()
        except Exception as e:
            print("[vision] CLIP недоступен (%s), включаю dummy" % e)
            return DummyVision()
    return DummyVision()

