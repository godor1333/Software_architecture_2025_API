# Честная оценка: CLIP zero-shot на data/eval/<label>/ -> accuracy, macro-F1
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image

EVAL_ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "eval")
OUT = os.path.join(os.path.dirname(__file__), "..", "artifacts", "metrics.json")

def main():
    from services.vision.classifier import make_classifier
    clf = make_classifier()
    y_true, y_pred = [], []
    for label in sorted(os.listdir(EVAL_ROOT)):
        d = os.path.join(EVAL_ROOT, label)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue
            img = Image.open(os.path.join(d, f))
            cat, score, _ = clf.predict(img)
            y_true.append(label)
            y_pred.append(cat)
    if not y_true:
        print("eval: data/eval пуст - выполните scripts/prepare_eval_data.py")
        sys.exit(2)
    labels = sorted(set(y_true) | set(y_pred))
    per = {}
    for lb in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lb and p == lb)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lb and p == lb)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lb and p != lb)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per[lb] = {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
                   "support": sum(1 for t in y_true if t == lb)}
    acc = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    macro_f1 = sum(v["f1"] for v in per.values()) / len(per)
    metrics = {
        "model": "CLIP zero-shot ViT-B/32",
        "n": len(y_true),
        "accuracy": round(acc, 3),
        "macro_f1": round(macro_f1, 3),
        "per_class": per,
        "notes": "Замечание преподавателя учтено: план при macro_f1 < 0.85 см. report.md п.13",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(metrics, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
