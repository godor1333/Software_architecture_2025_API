# Подготовка eval-датасета: синтетика / внешние датасеты / смешанный режим
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

LABELS = ["violence", "weapons", "drugs", "gambling", "scam", "spam", "benign"]
OUT_ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "eval")


def synth_for_label(label, n=60, seed=7):
    # Синтетические примеры для отладки пайплайна (нижняя оценка качества)
    from PIL import Image, ImageDraw
    import random
    rnd = random.Random(seed + sum(map(ord, label)))
    d = os.path.join(OUT_ROOT, label)
    os.makedirs(d, exist_ok=True)
    for i in range(n):
        img = Image.new("RGB", (256, 256),
                        (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)))
        dr = ImageDraw.Draw(img)
        for _ in range(rnd.randint(3, 10)):
            x0, y0 = rnd.randrange(180), rnd.randrange(180)
            dr.ellipse([x0, y0, x0 + rnd.randrange(30, 76), y0 + rnd.randrange(30, 76)],
                       fill=(rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)))
        img.save(os.path.join(d, "synth_%03d.jpg" % i), quality=80)


def import_dir(src, label, limit=None):
    import shutil
    d = os.path.join(OUT_ROOT, label)
    os.makedirs(d, exist_ok=True)
    files = [f for f in os.listdir(src)
             if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    if limit:
        files = files[:limit]
    for f in files:
        shutil.copy(os.path.join(src, f), os.path.join(d, "src_" + f))
    return len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["synth", "external", "mixed"], default="synth")
    ap.add_argument("--src", help="корень внешнего датасета с папками-классами")
    ap.add_argument("--map", help="JSON соответствия: {\"имя_папки\": \"label\"}")
    ap.add_argument("--per-class", type=int, default=200)
    args = ap.parse_args()
    if args.mode in ("synth", "mixed"):
        for lb in LABELS:
            synth_for_label(lb)
    if args.mode in ("external", "mixed"):
        if not args.src:
            sys.exit("--src обязателен для режимов external/mixed")
        mapping = json.loads(args.map) if args.map else {
            lb: lb for lb in LABELS if os.path.isdir(os.path.join(args.src, lb))}
        for src_name, label in mapping.items():
            src = os.path.join(args.src, src_name)
            if os.path.isdir(src):
                n = import_dir(src, label, args.per_class)
                print("%-12s <- %s (%d файлов)" % (label, src_name, n))
    for lb in LABELS:
        d = os.path.join(OUT_ROOT, lb)
        n = len(os.listdir(d)) if os.path.isdir(d) else 0
        print("eval/%-12s %d изображений" % (lb, n))


if __name__ == "__main__":
    main()
