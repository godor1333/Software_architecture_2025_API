# Linear probe поверх замороженных CLIP-эмбеддингов 
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
import joblib

EVAL_ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "eval")
OUT = os.path.join(os.path.dirname(__file__), "..", "artifacts", "linear_probe_metrics.json")

def load_dataset():
    from services.vision.classifier import CLIPZeroShot
    clf = CLIPZeroShot()
    X, y = [], []
    for label in sorted(os.listdir(EVAL_ROOT)):
        d = os.path.join(EVAL_ROOT, label)
        if not os.path.isdir(d):
            continue
        files = [f for f in sorted(os.listdir(d)) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        for f in files:
            img = Image.open(os.path.join(d, f)).convert("RGB")
            inputs = clf.processor(images=img, return_tensors="pt")
            feats = clf.model.get_image_features(**inputs).detach().numpy()[0]
            X.append(feats / np.linalg.norm(feats))
            y.append(label)
    return np.array(X), np.array(y), clf

def main():
    X, y, clf = load_dataset()
    if len(X) < 10:
        print("train: мало данных - подготовьте data/eval")
        sys.exit(2)
    # стратифицированный сплит 80/20
    from sklearn.model_selection import train_test_split
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42,
                                          stratify=y)
    head = LogisticRegression(max_iter=2000, C=1.0)
    head.fit(Xtr, ytr)
    pred = head.predict(Xte)
    metrics = {
        "model": "CLIP embeddings + LogisticRegression (linear probe)",
        "n_train": int(len(Xtr)), "n_test": int(len(Xte)),
        "accuracy": round(float(accuracy_score(yte, pred)), 3),
        "macro_f1": round(float(f1_score(yte, pred, average="macro")), 3),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    joblib.dump({"classes": list(head.classes_), "coef": head.coef_, "intercept": head.intercept_},
                os.path.join(os.path.dirname(OUT), "linear_probe.pkl"))
    json.dump(metrics, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
