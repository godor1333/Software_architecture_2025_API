import time
import uuid
import cv2
import numpy as np
from typing import Dict, Any, Optional
from ..models import CarDamageReport, SeverityLevel
from ..cv.preprocessor import ImagePreprocessor
from ..cv.detector import DamageInferenceEngine
from .strategy import IDamageDetectorStrategy
from .adapter import IStorageAdapter
from .repository import IDamageReportRepository

class PipelineContext:
    """Контекст, проходящий через все стадии конвейера (Pipeline Pattern)."""

    def __init__(self, raw_bytes: bytes, vehicle_vin: str = "VIN_UNKNOWN", client_id: str = "DEFAULT"):
        self.raw_bytes = raw_bytes
        self.vehicle_vin = vehicle_vin
        self.client_id = client_id
        self.original_bgr: Optional[np.ndarray] = None
        self.processed_bgr: Optional[np.ndarray] = None
        self.scale_ratio: float = 1.0
        self.padding: tuple = (0, 0)
        self.detected_boxes = []
        self.annotated_bgr: Optional[np.ndarray] = None
        self.raw_url: str = ""
        self.annotated_url: str = ""
        self.report: Optional[CarDamageReport] = None
        self.start_time: float = time.time()

class CarDamagePipeline:
    """Пайплайн инспекции и оценки повреждений автомобиля."""

    def __init__(
        self,
        detector_strategy: IDamageDetectorStrategy,
        storage_adapter: IStorageAdapter,
        report_repository: IDamageReportRepository
    ):
        self.detector_strategy = detector_strategy
        self.storage_adapter = storage_adapter
        self.report_repository = report_repository
        self.preprocessor = ImagePreprocessor()
        self.engine = DamageInferenceEngine()

    def stage_1_validation(self, ctx: PipelineContext) -> None:
        if not ctx.raw_bytes or len(ctx.raw_bytes) < 100:
            raise ValueError("Размер файла слишком мал или данные повреждены.")

    def stage_2_preprocessing(self, ctx: PipelineContext) -> None:
        res = self.preprocessor.process(ctx.raw_bytes)
        ctx.original_bgr = res["original_bgr"]
        ctx.processed_bgr = res["processed_bgr"]
        ctx.scale_ratio = res["scale_ratio"]
        ctx.padding = res["padding"]

    def stage_3_inference(self, ctx: PipelineContext) -> None:
        ctx.detected_boxes = self.detector_strategy.detect(ctx.original_bgr, ctx.processed_bgr)

    def stage_4_assessment(self, ctx: PipelineContext) -> None:
        ctx.annotated_bgr = self.engine.annotate_image(ctx.original_bgr, ctx.detected_boxes)

        # Расчет итоговой тяжести и стоимости
        total_cost = sum(b.estimated_repair_rub for b in ctx.detected_boxes)
        has_severe = any(b.severity == SeverityLevel.SEVERE for b in ctx.detected_boxes)
        has_moderate = any(b.severity == SeverityLevel.MODERATE for b in ctx.detected_boxes)

        if has_severe:
            overall_severity = SeverityLevel.SEVERE
        elif has_moderate or len(ctx.detected_boxes) >= 2:
            overall_severity = SeverityLevel.MODERATE
        else:
            overall_severity = SeverityLevel.MINOR

        elapsed_ms = (time.time() - ctx.start_time) * 1000.0

        ctx.report = CarDamageReport(
            vehicle_vin=ctx.vehicle_vin,
            client_id=ctx.client_id,
            raw_image_url="",
            annotated_image_url="",
            damages=ctx.detected_boxes,
            total_damages_count=len(ctx.detected_boxes),
            overall_severity=overall_severity,
            total_estimated_repair_rub=round(total_cost, 2),
            model_name=self.detector_strategy.name,
            processing_time_ms=round(elapsed_ms, 2)
        )

    def stage_5_storage_persistence(self, ctx: PipelineContext) -> None:
        rep_id = ctx.report.report_id
        # Кодируем аннотированное изображение
        _, enc_ann = cv2.imencode(".jpg", ctx.annotated_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        ann_bytes = enc_ann.tobytes()

        # Сохранение через StorageAdapter
        ctx.raw_url = self.storage_adapter.upload_image(ctx.raw_bytes, f"raw_{rep_id}.jpg")
        ctx.annotated_url = self.storage_adapter.upload_image(ann_bytes, f"annotated_{rep_id}.jpg")

        ctx.report.raw_image_url = ctx.raw_url
        ctx.report.annotated_image_url = ctx.annotated_url

        # Сохранение в Repository
        self.report_repository.save_report(ctx.report)

    def execute(self, ctx: PipelineContext) -> CarDamageReport:
        """Последовательное исполнение стадий пайплайна."""
        self.stage_1_validation(ctx)
        self.stage_2_preprocessing(ctx)
        self.stage_3_inference(ctx)
        self.stage_4_assessment(ctx)
        self.stage_5_storage_persistence(ctx)
        return ctx.report
