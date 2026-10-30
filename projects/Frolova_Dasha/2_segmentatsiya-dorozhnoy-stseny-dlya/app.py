"""Runnable pedagogical road-scene segmentation pipeline based on image colors."""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from collections import Counter
import importlib.util
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image
from PIL import ImageOps


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "scene.db"
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)
PALETTE = {"road": (80, 80, 80), "car": (220, 30, 30), "pedestrian": (255, 190, 20), "lane_marking": (245, 245, 245), "obstacle": (30, 30, 220), "other": (0, 0, 0)}

PRODUCTION_PACKAGES = {
    "PyTorch": "torch",
    "OpenCV": "cv2",
    "Transformers": "transformers",
    "Kafka (aiokafka)": "aiokafka",
    "MinIO (minio)": "minio",
    "PostgreSQL (asyncpg)": "asyncpg",
}


def production_enabled() -> bool:
    return os.environ.get("PRODUCTION_MODE", "").lower() in {"1", "true", "yes"}


def integration_status() -> dict[str, Any]:
    return {
        "packages": {label: bool(importlib.util.find_spec(module)) for label, module in PRODUCTION_PACKAGES.items()},
        "model": os.environ.get("SEGMENTATION_MODEL", "local-color-baseline"),
        "weights": os.environ.get("SEGMENTATION_MODEL", "not-configured"),
        "production_mode": production_enabled(),
        "network_probe": "not_run",
        "storage": "postgres-minio-kafka" if production_enabled() else "sqlite-artifacts-baseline",
    }


class FramePreprocessor:
    """Normalize an incoming frame before segmentation.

    The service accepts camera frames in arbitrary RGB/RGBA/JPEG/PNG form. EXIF
    orientation is applied and large frames are reduced to a bounded working
    size so the API and video pipeline have the same deterministic input stage.
    """

    def __init__(self, max_size: tuple[int, int] = (1280, 720)):
        self.max_size = max_size

    def process(self, image: Image.Image) -> Image.Image:
        normalized = ImageOps.exif_transpose(image).convert("RGB")
        normalized.thumbnail(self.max_size, Image.Resampling.LANCZOS)
        return normalized


class FrameObserver:
    """Observer contract for post-segmentation scene events."""

    def update(self, event: dict[str, Any]) -> None:
        raise NotImplementedError


class SceneAnalyticsObserver(FrameObserver):
    """Persist per-frame analytics in the local analytical SQLite store."""

    def update(self, event: dict[str, Any]) -> None:
        with db() as con:
            con.execute(
                """INSERT OR REPLACE INTO scene_analytics
                (frame_id, flight_id, captured_at, width, height, dominant_class,
                 road_share, car_share, pedestrian_share, lane_marking_share,
                 obstacle_share, other_share)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event["frame_id"], event["flight_id"], event["captured_at"],
                    event["width"], event["height"], event["dominant_class"],
                    event["class_share"].get("road", 0.0), event["class_share"].get("car", 0.0),
                    event["class_share"].get("pedestrian", 0.0), event["class_share"].get("lane_marking", 0.0),
                    event["class_share"].get("obstacle", 0.0), event["class_share"].get("other", 0.0),
                ),
            )


class SegmentationPipeline:
    """Pipeline pattern: preprocess -> segment -> analytics event."""

    def __init__(self, model_id: str | None = None):
        self.preprocessor = FramePreprocessor()
        self.strategy = segmentation_strategy(model_id)

    def run(self, image: Image.Image) -> tuple[Image.Image, dict[str, int], Image.Image]:
        prepared = self.preprocessor.process(image)
        mask, totals = self.strategy.predict(prepared)
        return prepared, totals, mask


class SegFormerAdapter:
    """Optional Hugging Face SegFormer inference adapter.

    Loading is explicit because it may download hundreds of megabytes.  The
    local baseline remains deterministic when no model ID is configured.
    """

    def __init__(self, model_id: str | None = None):
        model_id = model_id or os.environ.get("SEGMENTATION_MODEL")
        if not model_id:
            raise ValueError("SEGMENTATION_MODEL is required for SegFormer mode")
        from transformers import AutoImageProcessor, SegformerForSemanticSegmentation
        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = SegformerForSemanticSegmentation.from_pretrained(model_id)
        self.model.eval()

    def predict_labels(self, image: Image.Image):
        import torch
        import torch.nn.functional as F
        inputs = self.processor(images=image.convert("RGB"), return_tensors="pt")
        with torch.inference_mode():
            logits = self.model(**inputs).logits
            logits = F.interpolate(logits, size=(image.height,image.width), mode="bilinear", align_corners=False)
        return logits.argmax(dim=1)[0].cpu().numpy()

    def predict(self, image: Image.Image) -> Image.Image:
        labels = self.predict_labels(image)
        mask = Image.new("RGB", image.size, PALETTE["obstacle"])
        output = mask.load()
        class_map = {
            "road": "road", "sidewalk": "road", "parking": "road", "rail track": "road",
            "car": "car", "truck": "car", "bus": "car", "train": "car", "motorcycle": "car", "bicycle": "car",
            "person": "pedestrian", "rider": "pedestrian", "road line": "lane_marking",
            "traffic sign": "obstacle", "traffic light": "obstacle", "building": "obstacle",
            "wall": "obstacle", "fence": "obstacle", "pole": "obstacle", "vegetation": "obstacle",
            "terrain": "obstacle", "sky": "other", "unlabeled": "other",
        }
        id2label = getattr(self.model.config, "id2label", {})
        for y in range(image.height):
            for x in range(image.width):
                value = int(labels[y,x])
                source_name = str(id2label.get(value, "other")).lower()
                target_name = class_map.get(source_name, "other")
                output[x, y] = PALETTE[target_name]
        import numpy as np
        road = np.all(np.asarray(mask) == PALETTE['road'],axis=2)
        lane = detect_lane_markings(image,road)
        mask_array=np.asarray(mask).copy()
        mask_array[lane]=PALETTE['lane_marking']
        mask=Image.fromarray(mask_array)
        return mask


def detect_lane_markings(image: Image.Image, road_mask):
    """Find bright white/yellow candidate markings within the predicted road."""
    import cv2
    import numpy as np
    hsv=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2HSV)
    gray=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
    top_hat=cv2.morphologyEx(gray,cv2.MORPH_TOPHAT,cv2.getStructuringElement(cv2.MORPH_RECT,(15,15)))
    white=cv2.inRange(hsv,np.array([0,0,70],dtype=np.uint8),np.array([179,90,255],dtype=np.uint8))
    yellow=cv2.inRange(hsv,np.array([12,60,70],dtype=np.uint8),np.array([40,255,255],dtype=np.uint8))
    candidates=cv2.bitwise_and(cv2.bitwise_or(white,yellow),cv2.threshold(top_hat,10,255,cv2.THRESH_BINARY)[1])
    candidates=cv2.morphologyEx(candidates,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    return np.logical_and(candidates>0,road_mask)


def evaluate_segformer(model_id: str | None = None, image_path: str | Path | None = None) -> dict[str, Any]:
    """Run the configured Cityscapes SegFormer and persist a model-evidence record."""
    model_id = model_id or os.environ.get("SEGMENTATION_MODEL")
    if not model_id:
        raise ValueError("SEGMENTATION_MODEL is required for model evaluation")
    source_path = Path(image_path or (ARTIFACTS / "comma10k_image.png"))
    image = Image.open(source_path).convert("RGB")
    mask = SegFormerAdapter(model_id).predict(image)
    output_path = ARTIFACTS / "segformer_mask.png"
    mask.save(output_path)
    counts = {name: 0 for name in PALETTE}
    for pixel in mask.getdata():
        for name, color in PALETTE.items():
            if pixel == color:
                counts[name] += 1
                break
    total = image.width * image.height
    result = {
        "model": model_id,
        "weights_source": "Hugging Face Hub",
        "input": str(source_path.name),
        "pixels": total,
        "predicted_class_pixels": counts,
        "predicted_class_share": {name: round(value / total, 6) for name, value in counts.items()},
        "mask": output_path.name,
        "inference": "completed",
    }
    (ARTIFACTS / "segformer_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def evaluate_road_dataset(model_id: str | None = None) -> dict[str, Any]:
    """Compare road IoU on the packaged comma10k labelled sample."""
    import numpy as np
    model_id=model_id or os.environ.get("SEGMENTATION_MODEL")
    if not model_id: raise ValueError("SEGMENTATION_MODEL is required")
    image=Image.open(ARTIFACTS/"comma10k_image.png").convert("RGB")
    target=np.asarray(Image.open(ARTIFACTS/"comma10k_mask.png").convert("RGB"))
    truth=np.all(target == np.array([64,32,32]),axis=2)
    valid=np.any(target != np.array([204,0,255]),axis=2)
    model=SegFormerAdapter(model_id)
    ids=model.predict_labels(image)
    road_ids=[int(k) for k,v in model.model.config.id2label.items() if str(v).lower()=="road"]
    if not road_ids: raise ValueError("Model has no road class")
    prediction=np.isin(ids,road_ids)
    baseline=np.asarray(segment(image)[0])
    baseline_road=np.all(baseline == np.array(PALETTE["road"]),axis=2)
    def iou(pred):
        intersection=np.logical_and(np.logical_and(pred,truth),valid).sum()
        union=np.logical_and(np.logical_or(pred,truth),valid).sum()
        return round(float(intersection/union),4) if union else None
    result={"dataset":"comma10k","sample_count":1,"sample_id":"0000_0085e9e41513078a_2018-08-19--13-26-08_11_864","source":"https://github.com/commaai/comma10k","metric":"road IoU","segformer_road_iou":iou(prediction),"color_baseline_road_iou":iou(baseline_road),"excluded":"own car pixels","model":model_id,"limitation":"single labelled image; no separate lane-marking class in this Cityscapes model"}
    (ARTIFACTS/"road_iou_comparison.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


class KafkaFrameConsumer:
    """Contract adapter for the `frames.created` Kafka topic."""

    topic = "frames.created"

    async def consume_once(self) -> dict[str, Any]:
        from aiokafka import AIOKafkaConsumer
        consumer = AIOKafkaConsumer(self.topic, bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"), group_id="scene-segmentation")
        await consumer.start()
        try:
            message = await consumer.getone()
            return json.loads(message.value.decode("utf-8"))
        finally:
            await consumer.stop()


class SegmentationEventPublisher:
    """Publishes `frames.segmented` events for downstream analytics."""

    topic = "frames.segmented"

    async def publish(self, result: dict[str, Any]) -> None:
        from aiokafka import AIOKafkaProducer
        producer = AIOKafkaProducer(bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"))
        await producer.start()
        try:
            await producer.send_and_wait(self.topic, json.dumps(result, ensure_ascii=False).encode("utf-8"), key=result["frame_id"].encode("utf-8"))
        finally:
            await producer.stop()


class MinioFrameStore:
    """MinIO adapter for source frames and masks."""

    def __init__(self):
        from minio import Minio
        self.client = Minio(os.environ.get("MINIO_ENDPOINT", "minio:9000"), access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"), secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"), secure=False)

    def put(self, bucket: str, name: str, data: bytes, content_type: str = "image/png") -> None:
        from io import BytesIO
        from minio.error import S3Error
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)
        self.client.put_object(bucket, name, BytesIO(data), len(data), content_type=content_type)


class PostgresFrameRepository:
    """Persist frame metadata independently of local demonstration storage."""

    async def save(self, frame: dict[str, Any]) -> None:
        import asyncpg

        con = await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            await con.execute("""CREATE TABLE IF NOT EXISTS segmented_frames (
                frame_id text primary key, flight_id text not null, captured_at timestamptz not null,
                source_object text not null, mask_object text not null, class_share jsonb not null)""")
            await con.execute("CREATE INDEX IF NOT EXISTS idx_segmented_frames_flight_time ON segmented_frames(flight_id, captured_at)")
            await con.execute("""CREATE TABLE IF NOT EXISTS scene_analytics (
                frame_id text primary key references segmented_frames(frame_id), flight_id text not null,
                captured_at timestamptz not null, width integer not null, height integer not null,
                dominant_class text not null, class_share jsonb not null)""")
            await con.execute("CREATE INDEX IF NOT EXISTS idx_scene_analytics_flight_time ON scene_analytics(flight_id, captured_at)")
            await con.execute("""INSERT INTO segmented_frames VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT(frame_id) DO UPDATE SET captured_at=EXCLUDED.captured_at,
                source_object=EXCLUDED.source_object, mask_object=EXCLUDED.mask_object,
                class_share=EXCLUDED.class_share""",
                frame["frame_id"], frame["flight_id"], datetime.fromisoformat(frame["captured_at"]),
                frame["source_object"], frame["mask_object"],
                json.dumps(frame["class_share"], ensure_ascii=False))
            await con.execute("""INSERT INTO scene_analytics
                (frame_id, flight_id, captured_at, width, height, dominant_class, class_share)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT(frame_id) DO UPDATE SET class_share=EXCLUDED.class_share,
                dominant_class=EXCLUDED.dominant_class""",
                frame["frame_id"], frame["flight_id"], datetime.fromisoformat(frame["captured_at"]),
                frame["width"], frame["height"], frame["dominant_class"],
                json.dumps(frame["class_share"], ensure_ascii=False))
        finally:
            await con.close()

@contextmanager
def db():
    con=sqlite3.connect(DB_PATH)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS frames(frame_id TEXT PRIMARY KEY, flight_id TEXT NOT NULL, captured_at TEXT NOT NULL, image_path TEXT NOT NULL, mask_path TEXT NOT NULL, metrics TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_frames_flight_time ON frames(flight_id, captured_at);
        CREATE TABLE IF NOT EXISTS scene_analytics(
            frame_id TEXT PRIMARY KEY, flight_id TEXT NOT NULL, captured_at TEXT NOT NULL,
            width INTEGER NOT NULL, height INTEGER NOT NULL, dominant_class TEXT NOT NULL,
            road_share REAL NOT NULL, car_share REAL NOT NULL, pedestrian_share REAL NOT NULL,
            lane_marking_share REAL NOT NULL, obstacle_share REAL NOT NULL, other_share REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_scene_analytics_flight_time ON scene_analytics(flight_id, captured_at);
        CREATE INDEX IF NOT EXISTS idx_scene_analytics_dominant ON scene_analytics(dominant_class);
        """)


def segment(image: Image.Image) -> tuple[Image.Image, dict[str, int]]:
    source = image.convert("RGB")
    mask = Image.new("RGB", source.size, PALETTE["road"])
    pixels, out = source.load(), mask.load()
    totals = {key: 0 for key in PALETTE}
    for y in range(source.height):
        for x in range(source.width):
            r, g, b = pixels[x, y]
            if r > 170 and g < 110 and b < 110:
                cls = "car"
            elif r > 190 and g > 140 and b < 80:
                cls = "pedestrian"
            elif r > 215 and g > 215 and b > 215:
                cls = "lane_marking"
            elif b > 150 and r < 110:
                cls = "obstacle"
            else:
                cls = "road"
            out[x, y] = PALETTE[cls]
            totals[cls] += 1
    return mask, totals


def segmentation_metrics(prediction: Image.Image, target: Image.Image) -> dict[str, Any]:
    """Compute per-class IoU and mean IoU for a saved mask pair."""
    predicted = prediction.convert("RGB")
    expected = target.convert("RGB").resize(predicted.size)
    result: dict[str, float | None] = {}
    for name, color in PALETTE.items():
        intersection = union = 0
        for left, right in zip(predicted.getdata(), expected.getdata()):
            left_match, right_match = left == color, right == color
            intersection += int(left_match and right_match)
            union += int(left_match or right_match)
        result[name] = round(intersection / union, 4) if union else None
    valid = [x for x in result.values() if x is not None]
    return {"per_class_iou": result, "mIoU": round(sum(valid) / len(valid), 4) if valid else 0.0}


def evaluate_segmentation() -> dict[str, Any]:
    """Evaluate the deterministic baseline on the generated labelled frame."""
    source = Image.new("RGB", (160, 90), PALETTE["road"])
    pixels = source.load()
    for x in range(70, 90):
        for y in range(90): pixels[x, y] = PALETTE["lane_marking"]
    for x in range(20, 55):
        for y in range(35, 65): pixels[x, y] = PALETTE["car"]
    for x in range(120, 130):
        for y in range(30, 70): pixels[x, y] = PALETTE["pedestrian"]
    prediction, _ = segment(source)
    metrics = segmentation_metrics(prediction, source)
    metrics.update({"model": "color-baseline", "samples": 1, "seed": 20261027})
    (ARTIFACTS / "segmentation_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


def png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def mirror_frame_to_production(result: dict[str, Any], source: bytes, mask: bytes) -> None:
    """Mirror one accepted frame to the services declared in ``services.yml``."""
    bucket = os.environ.get("MINIO_BUCKET", "scene-frames")
    result["source_object"] = f"frames/{result['frame_id']}.png"
    result["mask_object"] = f"masks/{result['frame_id']}.png"
    store = MinioFrameStore()
    store.put(bucket, result["source_object"], source)
    store.put(bucket, result["mask_object"], mask)
    asyncio.run(PostgresFrameRepository().save(result))
    asyncio.run(SegmentationEventPublisher().publish({
        "frame_id": result["frame_id"], "flight_id": result["flight_id"],
        "captured_at": result["captured_at"], "class_share": result["class_share"],
        "source_object": result["source_object"], "mask_object": result["mask_object"],
        "width": result["width"], "height": result["height"],
        "dominant_class": result["dominant_class"], "preprocessing": result["preprocessing"],
    }))
    result["production"] = {"minio_bucket": bucket, "postgres": True, "kafka_topic": SegmentationEventPublisher.topic}


class ColorSegmentationStrategy:
    def predict(self, image): return segment(image)

class ModelSegmentationStrategy:
    def __init__(self, model_id): self.adapter=SegFormerAdapter(model_id)
    def predict(self, image):
        mask=self.adapter.predict(image)
        counts=Counter(mask.getdata())
        return mask, {name:counts[color] for name,color in PALETTE.items()}

def segmentation_strategy(model_id):
    return ModelSegmentationStrategy(model_id) if model_id else ColorSegmentationStrategy()

def store_frame(frame_id: str, flight_id: str, image_bytes: bytes) -> dict[str, Any]:
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', frame_id):
        raise ValueError('frame_id must contain only ASCII letters, digits, _ or -')
    if not flight_id or len(flight_id) > 120:
        raise ValueError('flight_id must be 1 to 120 characters')
    init_db()
    try:
        original = Image.open(BytesIO(image_bytes))
        image, totals, mask = SegmentationPipeline(os.environ.get("SEGMENTATION_MODEL")).run(original)
    except Exception as exc:
        raise ValueError(f"invalid image: {exc}") from exc
    source_path, mask_path = ARTIFACTS / f"{frame_id}.png", ARTIFACTS / f"{frame_id}_mask.png"
    image.convert("RGB").save(source_path)
    mask.save(mask_path)
    metrics = {key: round(value / (image.width * image.height), 4) for key, value in totals.items()}
    captured_at = datetime.now(timezone.utc).isoformat()
    with db() as con:
        con.execute("INSERT OR REPLACE INTO frames VALUES (?, ?, ?, ?, ?, ?)", (frame_id, flight_id, captured_at, str(source_path.name), str(mask_path.name), json.dumps(metrics)))
    dominant_class = max(metrics, key=metrics.get)
    result = {"frame_id": frame_id, "flight_id": flight_id, "mask": mask_path.name, "class_share": metrics, "captured_at": captured_at,
              "width": image.width, "height": image.height, "dominant_class": dominant_class,
              "preprocessing": {"orientation": "EXIF applied", "color_space": "RGB", "max_size": [1280, 720]}}
    SceneAnalyticsObserver().update(result)
    if production_enabled():
        mirror_frame_to_production(result, png_bytes(image), png_bytes(mask))
    return result


def get_frame(frame_id: str) -> dict[str, Any] | None:
    init_db()
    with db() as con:
        row = con.execute("SELECT frame_id, flight_id, captured_at, image_path, mask_path, metrics FROM frames WHERE frame_id=?", (frame_id,)).fetchone()
    if not row:
        return None
    return {"frame_id": row[0], "flight_id": row[1], "captured_at": row[2], "image": row[3], "mask": row[4], "class_share": json.loads(row[5])}


def summary() -> dict[str, Any]:
    init_db()
    with db() as con:
        count = con.execute("SELECT COUNT(*) FROM frames").fetchone()[0]
    with db() as con:
        rows = con.execute("SELECT dominant_class, COUNT(*) FROM scene_analytics GROUP BY dominant_class ORDER BY COUNT(*) DESC").fetchall()
        flights = con.execute("SELECT COUNT(DISTINCT flight_id) FROM scene_analytics").fetchone()[0]
    return {"frames": count, "flights": flights, "classes": list(PALETTE),
            "dominant_classes": {key: value for key, value in rows},
            "backend": os.environ.get("SEGMENTATION_MODEL", "color-baseline"),
            "metrics": str((ARTIFACTS / "segmentation_metrics.json").name) if (ARTIFACTS / "segmentation_metrics.json").exists() else None}


def analytics(flight_id: str | None = None) -> dict[str, Any]:
    """Return dashboard-ready aggregates for a flight or all flights."""
    if production_enabled():
        async def query_postgres():
            import asyncpg
            con = await asyncpg.connect(os.environ["DATABASE_URL"])
            try:
                exists = await con.fetchval("SELECT to_regclass('public.scene_analytics')")
                if not exists:
                    return []
                if flight_id:
                    records = await con.fetch("SELECT frame_id,flight_id,captured_at,width,height,dominant_class,class_share FROM scene_analytics WHERE flight_id=$1 ORDER BY captured_at", flight_id)
                else:
                    records = await con.fetch("SELECT frame_id,flight_id,captured_at,width,height,dominant_class,class_share FROM scene_analytics ORDER BY captured_at")
                items = []
                for row in records:
                    values = row['class_share']
                    shares = json.loads(values) if isinstance(values, str) else values
                    item = {key: row[key] for key in ('frame_id','flight_id','width','height','dominant_class')}
                    item['captured_at'] = row['captured_at'].isoformat()
                    item.update({name + '_share': shares.get(name, 0.0) for name in PALETTE})
                    items.append(item)
                return items
            finally:
                await con.close()
        items = asyncio.run(query_postgres())
        return {"flight_id": flight_id, "frames": len(items), "items": items}
    init_db()
    fields = ["frame_id", "flight_id", "captured_at", "width", "height", "dominant_class", "road_share", "car_share", "pedestrian_share", "lane_marking_share", "obstacle_share", "other_share"]
    with db() as con:
        if flight_id:
            rows = con.execute("SELECT " + ",".join(fields) + " FROM scene_analytics WHERE flight_id=? ORDER BY captured_at", (flight_id,)).fetchall()
        else:
            rows = con.execute("SELECT " + ",".join(fields) + " FROM scene_analytics ORDER BY captured_at").fetchall()
    return {"flight_id": flight_id, "frames": len(rows), "items": [dict(zip(fields, row)) for row in rows]}


def process_video_stream(frame_id_prefix: str, flight_id: str, frame_paths: list[str | Path]) -> dict[str, Any]:
    """Process a finite video stream represented by ordered image frames."""
    results = []
    for index, path in enumerate(frame_paths):
        frame_id = f"{frame_id_prefix}-{index:04d}"
        results.append(store_frame(frame_id, flight_id, Path(path).read_bytes()))
    return {"stream_id": frame_id_prefix, "flight_id": flight_id, "frames": len(results), "results": results}


class Api(BaseHTTPRequestHandler):
    def respond(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_POST(self):
        if self.path != "/api/v1/frames": return self.respond(404, {"error": "not found"})
        try:
            frame_id = self.headers.get("X-Frame-Id")
            flight_id = self.headers.get("X-Flight-Id")
            if not frame_id or not flight_id: raise ValueError("X-Frame-Id and X-Flight-Id headers are required")
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if not body: raise ValueError("image body is required")
            self.respond(201, store_frame(frame_id, flight_id, body))
        except Exception as error:
            self.respond(422, {"error": str(error)})

    def do_GET(self):
        if self.path == "/health": return self.respond(200, {"status": "ok", "database": DB_PATH.exists(), "artifact_dir": ARTIFACTS.exists()})
        if self.path == "/api/v1/summary": return self.respond(200, summary())
        if self.path == "/api/v1/analytics": return self.respond(200, analytics())
        if self.path.startswith("/api/v1/analytics/"):
            return self.respond(200, analytics(self.path.rsplit("/", 1)[-1]))
        if self.path.startswith("/api/v1/frames/"):
            item = get_frame(self.path.rsplit("/", 1)[-1]); return self.respond(200 if item else 404, item or {"error": "frame not found"})
        return self.respond(404, {"error": "not found"})

    def log_message(self, fmt, *args): return


def sample_image(path: Path):
    image = Image.new("RGB", (160, 90), PALETTE["road"])
    px = image.load()
    for x in range(70, 90):
        for y in range(0, 90): px[x, y] = PALETTE["lane_marking"]
    for x in range(20, 55):
        for y in range(35, 65): px[x, y] = PALETTE["car"]
    for x in range(120, 130):
        for y in range(30, 70): px[x, y] = PALETTE["pedestrian"]
    image.save(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--serve", action="store_true"); parser.add_argument("--port", type=int, default=8012); parser.add_argument("--demo", action="store_true"); parser.add_argument("--evaluate", action="store_true"); parser.add_argument("--evaluate-model", action="store_true"); parser.add_argument("--evaluate-road", action="store_true"); parser.add_argument("--integration-status", action="store_true"); args = parser.parse_args()
    if args.demo:
        demo = ARTIFACTS / "demo.png"; sample_image(demo); print(json.dumps(store_frame("frame-demo", "flight-demo", demo.read_bytes()), ensure_ascii=False, indent=2))
    if args.evaluate: print(json.dumps(evaluate_segmentation(), ensure_ascii=False, indent=2))
    if args.evaluate_model: print(json.dumps(evaluate_segformer(), ensure_ascii=False, indent=2))
    if args.evaluate_road: print(json.dumps(evaluate_road_dataset(), ensure_ascii=False, indent=2))
    if args.integration_status: print(json.dumps(integration_status(), ensure_ascii=False, indent=2))
    if args.serve: init_db(); print(f"Scene API: http://127.0.0.1:{args.port}"); ThreadingHTTPServer(("0.0.0.0", args.port), Api).serve_forever()
