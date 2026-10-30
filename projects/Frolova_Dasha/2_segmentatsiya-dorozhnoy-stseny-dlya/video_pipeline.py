"""Video-stream adapter for the road-scene segmentation project.

The API works with individual frames; this adapter turns an MP4 stream into
ordered PNG frames and sends every frame through the same preprocessing,
segmentation and analytics pipeline.  It also creates a deterministic demo
stream for local verification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

import app


def create_demo_video(path: str | Path, frame_count: int = 8, size: tuple[int, int] = (320, 180)) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 4.0, size)
    if not writer.isOpened():
        raise RuntimeError("OpenCV MP4 writer is unavailable")
    width, height = size
    for index in range(frame_count):
        frame = np.full((height, width, 3), (80, 80, 80), dtype=np.uint8)
        cv2.rectangle(frame, (30 + index * 3, 65), (100 + index * 3, 135), (30, 30, 220), -1)
        cv2.rectangle(frame, (220, 55), (245, 125), (20, 190, 255), -1)
        cv2.line(frame, (150, 0), (150, height), (245, 245, 245), 5)
        writer.write(frame)
    writer.release()
    return path


def process_video(path: str | Path, flight_id: str, prefix: str = "video", max_frames: int = 30) -> dict:
    path = Path(path)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video stream: {path}")
    results = []
    try:
        index = 0
        while index < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            ok, encoded = cv2.imencode(".png", frame)
            if not ok:
                raise RuntimeError(f"Cannot encode frame {index}")
            frame_id = f"{prefix}-{index:04d}"
            results.append(app.store_frame(frame_id, flight_id, encoded.tobytes()))
            index += 1
    finally:
        capture.release()
    return {"stream": str(path.name), "flight_id": flight_id, "frames_processed": len(results), "results": results}


def send_video_to_api(path: str | Path, flight_id: str, api_url: str, prefix: str = "video", max_frames: int = 30) -> dict:
    """Submit video frames to a running API so dashboard and worker use shared storage."""
    from urllib.request import Request, urlopen
    path = Path(path)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video stream: {path}")
    results = []
    try:
        while len(results) < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            ok, encoded = cv2.imencode('.png', frame)
            if not ok:
                raise RuntimeError('Cannot encode video frame')
            frame_id = f'{prefix}-{len(results):04d}'
            req = Request(api_url.rstrip('/') + '/api/v1/frames', data=encoded.tobytes(),
                          headers={'X-Frame-Id': frame_id, 'X-Flight-Id': flight_id, 'Content-Type': 'image/png'}, method='POST')
            with urlopen(req, timeout=180) as response:
                results.append(json.load(response))
    finally:
        capture.release()
    return {"stream": path.name, "flight_id": flight_id, "frames_processed": len(results), "results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--flight-id", default="flight-demo")
    parser.add_argument("--max-frames", type=int, default=30)
    parser.add_argument("--api-url", help="Optional FastAPI base URL; submit frames to the shared API analytics store")
    args = parser.parse_args()
    source = args.input
    if args.demo:
        source = app.ARTIFACTS / "demo_stream.mp4"
        create_demo_video(source)
    if source is None:
        parser.error("use --input VIDEO or --demo")
    if args.api_url:
        result = send_video_to_api(source, args.flight_id, args.api_url, max_frames=args.max_frames)
    else:
        result = process_video(source, args.flight_id, max_frames=args.max_frames)
    out = app.ARTIFACTS / "stream_run.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
