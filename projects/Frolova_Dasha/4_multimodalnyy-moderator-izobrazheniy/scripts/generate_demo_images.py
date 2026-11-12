# Генератор детерминированных демо-изображений (структурные, уникальный pHash)
import os
import math
import random
import json

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "demo")
os.makedirs(OUT, exist_ok=True)

def _font(size=28):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()

def gradient_bg(w, h, seed):
    rnd = random.Random(seed)
    c1 = (rnd.randint(20, 90), rnd.randint(20, 90), rnd.randint(20, 90))
    c2 = (rnd.randint(150, 240), rnd.randint(150, 240), rnd.randint(150, 240))
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        for x in range(w):
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * (x / (w - 1) * 0.5 + t * 0.5)) for i in range(3))
    return img

def draw_violence(img):
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 360, 360], outline=(200, 0, 0), width=6)
    d.line([80, 320, 320, 80], fill=(150, 0, 0), width=10)
    d.line([80, 80, 320, 320], fill=(150, 0, 0), width=10)
    d.text((100, 20), "FIGHT VIOLENCE", fill=(200, 0, 0), font=_font(30))

def draw_weapons(img):
    d = ImageDraw.Draw(img)
    d.polygon([(80, 200), (320, 200), (320, 170), (240, 170), (230, 140), (200, 150), (200, 170), (80, 170)],
              fill=(60, 60, 60))
    d.rectangle([110, 200, 150, 260], fill=(40, 40, 40))
    d.text((90, 280), "FIREARM", fill=(60, 60, 60), font=_font(30))

def draw_drugs(img):
    d = ImageDraw.Draw(img)
    for cx, cy, r in [(120, 160, 40), (280, 240, 40), (200, 300, 30)]:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(90, 160, 60), outline=(40, 90, 30), width=4)
    d.line([60, 60, 340, 340], fill=(90, 160, 60), width=5)
    d.text((90, 20), "PILLS NARCOTIC", fill=(40, 90, 30), font=_font(28))

def draw_gambling(img):
    d = ImageDraw.Draw(img)
    for cx, cy, r, col in [(130, 150, 45, (200, 20, 20)), (270, 150, 45, (20, 20, 200)),
                           (200, 260, 45, (200, 20, 20))]:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    d.text((110, 330), "CASINO BETS", fill=(255, 200, 0), font=_font(30))

def draw_scam(img):
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 380, 380], fill=(255, 235, 0))
    d.text((60, 60), "YOU WIN!", fill=(200, 0, 0), font=_font(48))
    d.text((40, 140), "FREE 1000 USD", fill=(0, 0, 160), font=_font(36))
    d.text((40, 220), "CLICK NOW!", fill=(200, 0, 0), font=_font(36))

def draw_spam(img):
    d = ImageDraw.Draw(img)
    for i in range(6):
        d.rectangle([20 + i * 60, 30 + (i % 2) * 60, 70 + i * 60, 90 + (i % 2) * 60],
                    fill=(255, 0, 255), outline=(0, 0, 0))
        d.text((24 + i * 60, 40 + (i % 2) * 60), "BUY", fill=(255, 255, 0), font=_font(20))
    d.text((60, 320), "SALE SALE SALE", fill=(255, 0, 0), font=_font(32))

def draw_benign_1(img):
    d = ImageDraw.Draw(img)
    d.ellipse([40, 40, 140, 140], fill=(250, 210, 60))  # солнце
    d.rectangle([0, 300, 400, 400], fill=(60, 160, 60))  # поле
    d.polygon([(200, 120), (160, 300), (240, 300)], fill=(90, 70, 40))  # ёлка

def draw_benign_2(img):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 280, 400, 400], fill=(180, 140, 100))  # стол
    d.ellipse([140, 180, 260, 290], fill=(230, 180, 140))  # еда
    d.ellipse([60, 240, 120, 300], fill=(200, 60, 60))
    d.ellipse([280, 240, 340, 300], fill=(200, 60, 60))

DEMOS = [
    ("violence", draw_violence), ("weapons", draw_weapons), ("drugs", draw_drugs),
    ("gambling", draw_gambling), ("scam", draw_scam), ("spam", draw_spam),
    ("benign_park", draw_benign_1), ("benign_food", draw_benign_2),
]

def main():
    manifest = []
    for i, (name, drawer) in enumerate(DEMOS):
        img = gradient_bg(400, 400, seed=42 + i)
        drawer(img)
        # сидированный шум делает pHash уникальным при детерминированной генерации
        rnd = random.Random(1000 + i)
        px = img.load()
        for _ in range(1500):
            x, y = rnd.randrange(400), rnd.randrange(400)
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, r + rnd.randint(-25, 25))),
                        max(0, min(255, g + rnd.randint(-25, 25))),
                        max(0, min(255, b + rnd.randint(-25, 25))))
        fname = "demo_%02d_%s.jpg" % (i, name)
        img.save(os.path.join(OUT, fname), quality=88)
        manifest.append({"file": fname, "expected_category": name.split("_")[0]})
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("generated %d demo images -> %s" % (len(manifest), OUT))

if __name__ == "__main__":
    main()
