import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
from PIL import Image, ImageDraw
from services.vision.main import phash, hamming

def structured_img(seed):
    rnd = random.Random(seed)
    img = Image.new("RGB", (200, 200), (rnd.randint(30, 90),) * 3)
    d = ImageDraw.Draw(img)
    for _ in range(8):
        x0, y0 = rnd.randrange(140), rnd.randrange(140)
        d.ellipse([x0, y0, x0 + rnd.randrange(20, 60), y0 + rnd.randrange(20, 60)],
                  fill=(rnd.randint(100, 255), rnd.randint(100, 255), rnd.randint(100, 255)))
    return img

def test_structured_images_unique_phash():
    hashes = [phash(structured_img(s)) for s in range(8)]
    assert len(set(hashes)) == 8, "pHash вырождается: %s" % hashes

def test_phash_stable_to_small_jpeg_like_noise():
    img = structured_img(5)
    h1 = phash(img)
    px = img.load()
    rnd = random.Random(1)
    for _ in range(200):
        x, y = rnd.randrange(200), rnd.randrange(200)
        r, g, b = px[x, y]
        px[x, y] = (min(255, r + 12), g, b)
    assert hamming(h1, phash(img)) <= 8

def test_flat_images_degenerate():
    # плоские цвета дают одинаковый хэш - это и был баг первой сборки
    h1 = phash(Image.new("RGB", (64, 64), (128, 128, 128)))
    h2 = phash(Image.new("RGB", (64, 64), (128, 128, 128)))
    assert h1 == h2
