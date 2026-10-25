import io
import pytest
from fastapi.testclient import TestClient
from project_2_car_damage_detection.api.main import app
from project_2_car_damage_detection.cv.preprocessor import ImagePreprocessor
from project_2_car_damage_detection.patterns.factory import DetectorFactory
from project_2_car_damage_detection.patterns.adapter import LocalFallbackStorageAdapter
from project_2_car_damage_detection.patterns.repository import InMemoryReportRepository
from project_2_car_damage_detection.patterns.pipeline import CarDamagePipeline, PipelineContext
from project_2_car_damage_detection.cv.demo_inspection import generate_sample_damaged_car_image
from project_2_car_damage_detection.models import DamageClass, SeverityLevel

client = TestClient(app)

@pytest.fixture
def sample_image_bytes():
    return generate_sample_damaged_car_image()

def test_image_preprocessor(sample_image_bytes):
    preprocessor = ImagePreprocessor(target_size=640)
    res = preprocessor.process(sample_image_bytes)

    assert "original_bgr" in res
    assert "processed_bgr" in res
    assert res["processed_bgr"].shape == (640, 640, 3)
    assert res["scale_ratio"] > 0.0

def test_detector_factory():
    fast_det = DetectorFactory.get_detector("yolov8_fast")
    assert "YOLOv8" in fast_det.name

    deep_det = DetectorFactory.get_detector("mask_rcnn_deep")
    assert "MaskRCNN" in deep_det.name

    with pytest.raises(ValueError):
        DetectorFactory.get_detector("non_existent_engine")

def test_pipeline_execution(sample_image_bytes):
    detector = DetectorFactory.get_detector("yolov8_fast")
    storage = LocalFallbackStorageAdapter()
    repo = InMemoryReportRepository()

    pipeline = CarDamagePipeline(
        detector_strategy=detector,
        storage_adapter=storage,
        report_repository=repo
    )

    ctx = PipelineContext(
        raw_bytes=sample_image_bytes,
        vehicle_vin="TESTVIN12345",
        client_id="test_client"
    )

    report = pipeline.execute(ctx)
    assert report.total_damages_count > 0
    assert report.total_estimated_repair_rub > 0
    assert report.raw_image_url != ""
    assert report.annotated_image_url != ""
    assert repo.get_by_id(report.report_id) is not None

def test_api_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_api_inspect_endpoint(sample_image_bytes):
    files = {"file": ("test_car.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")}
    data = {"vehicle_vin": "XTA210999999", "strategy": "yolov8_fast"}
    resp = client.post("/api/v1/damage/inspect", files=files, data=data)

    assert resp.status_code == 200
    body = resp.json()
    assert "report_id" in body
    assert body["total_damages_count"] >= 1
    assert body["total_estimated_repair_rub"] > 1000

def test_api_metrics_endpoint():
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    metrics = resp.json()
    assert "total_inspections" in metrics
    assert "damage_distribution" in metrics
