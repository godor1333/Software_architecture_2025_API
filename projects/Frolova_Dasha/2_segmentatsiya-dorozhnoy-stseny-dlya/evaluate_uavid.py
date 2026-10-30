"""Evaluate SegFormer on separately supplied UAVid RGB images and color masks.

This script reports only classes with matching labels: road, car, pedestrian.
UAVid does not provide a distinct lane-marking label; building/vegetation are
not a ground truth for arbitrary navigational obstacles. No scores are invented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from app import PALETTE, FramePreprocessor, SegFormerAdapter

UAVID = {
    'road': [(128, 64, 128)],
    'car': [(192, 0, 192), (64, 0, 128)],
    'pedestrian': [(64, 64, 0)],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, required=True, help='UAVid root with Images and Labels under sequence folders')
    parser.add_argument('--model', default='nvidia/segformer-b0-finetuned-cityscapes-1024-1024')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--output', type=Path, default=Path('artifacts/uavid_metrics.json'))
    args = parser.parse_args()
    pairs = []
    for image in sorted(args.data_dir.rglob('Images/*.png')):
        label = image.parent.parent / 'Labels' / image.name
        if label.exists():
            pairs.append((image, label))
    pairs = pairs[:args.limit]
    if not pairs:
        parser.error('no matching Images/*.png and Labels/*.png pairs found')
    adapter = SegFormerAdapter(args.model)
    sums = {key: [0, 0] for key in UAVID}
    rows = []
    for image_path, label_path in pairs:
        image = FramePreprocessor().process(Image.open(image_path))
        target = Image.open(label_path).convert('RGB').resize(image.size, Image.Resampling.NEAREST)
        pred = np.asarray(adapter.predict(image)); truth = np.asarray(target)
        row = {'image': str(image_path.relative_to(args.data_dir)),
               'image_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
               'label_sha256': hashlib.sha256(label_path.read_bytes()).hexdigest()}
        for name, colors in UAVID.items():
            expected = np.zeros(truth.shape[:2], dtype=bool)
            for color in colors:
                expected |= np.all(truth == color, axis=2)
            predicted = np.all(pred == PALETTE[name], axis=2)
            intersection = int((expected & predicted).sum())
            union = int((expected | predicted).sum())
            sums[name][0] += intersection; sums[name][1] += union
            row[name + '_iou'] = round(intersection / union, 4) if union else None
        rows.append(row)
    result = {'dataset': 'UAVid', 'model': args.model, 'samples': len(rows),
              'pooled_iou': {name: round(a / b, 4) if b else None for name, (a, b) in sums.items()},
              'limitations': 'UAVid has no separate lane-marking or general obstacle ground truth. Model is Cityscapes pretrained; no UAV fine-tuning is implied.',
              'rows': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
