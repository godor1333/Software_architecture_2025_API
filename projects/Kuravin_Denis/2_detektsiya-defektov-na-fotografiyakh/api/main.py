import base64
import time
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from ..models import CarDamageReport, InspectionSummaryMetrics
from ..config import settings
from ..patterns.factory import DetectorFactory
from ..patterns.adapter import LocalFallbackStorageAdapter, MinIOStorageAdapter, IStorageAdapter
from ..patterns.repository import InMemoryReportRepository, IDamageReportRepository
from ..patterns.pipeline import CarDamagePipeline, PipelineContext

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Компьютерное зрение и оценка повреждений кузова автомобилей (YOLOv8 / Mask R-CNN)"
)

# Синглтоны инфраструктуры
storage_adapter: IStorageAdapter = LocalFallbackStorageAdapter()
report_repository: IDamageReportRepository = InMemoryReportRepository()

@app.post("/api/v1/damage/inspect", response_model=CarDamageReport, tags=["Inspection"])
async def inspect_vehicle_photo(
    file: UploadFile = File(...),
    vehicle_vin: str = Form("XTA210900Y1234567"),
    client_id: str = Form("insurance_corp_1"),
    strategy: str = Form("yolov8_fast")
):
    """Прием фотографии автомобиля, запуск CV-пайплайна и формирование сметы ремонта."""
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Передан пустой файл.")

    detector = DetectorFactory.get_detector(strategy)
    pipeline = CarDamagePipeline(
        detector_strategy=detector,
        storage_adapter=storage_adapter,
        report_repository=report_repository
    )

    ctx = PipelineContext(
        raw_bytes=image_bytes,
        vehicle_vin=vehicle_vin,
        client_id=client_id
    )

    try:
        report = pipeline.execute(ctx)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки изображения: {str(e)}")

@app.get("/api/v1/damage/reports/{report_id}", response_model=CarDamageReport, tags=["Reports"])
def get_report(report_id: str):
    """Получение сохраненного отчета по идентификатору."""
    report = report_repository.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчет с указанным ID не найден.")
    return report

@app.get("/api/v1/reports", response_model=List[CarDamageReport], tags=["Reports"])
def list_reports(limit: int = Query(50, ge=1, le=100)):
    """Список последних инспекций."""
    return report_repository.list_reports(limit=limit)

@app.get("/api/v1/metrics", response_model=InspectionSummaryMetrics, tags=["Analytics"])
def get_metrics():
    """Сводная аналитика по видам выявленных повреждений и средней стоимости ремонта."""
    return report_repository.get_summary_metrics()

@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Проверка доступности сервиса."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "default_strategy": settings.default_detector_strategy,
        "storage": type(storage_adapter).__name__,
        "repository": type(report_repository).__name__
    }
