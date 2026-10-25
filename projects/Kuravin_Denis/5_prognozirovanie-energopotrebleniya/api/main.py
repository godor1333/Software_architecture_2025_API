import time
from typing import List
from fastapi import FastAPI, HTTPException, Query
from ..models import (
    MeterReadingEvent,
    EnergyForecastRequest,
    EnergyForecastResponse,
    AnomalyAlert,
    BuildingEnergyStats
)
from ..config import settings
from ..patterns.strategy import XGBoostForecastingStrategy, BaselinePersistenceStrategy
from ..patterns.observer import EnergyAlertSubject, OverloadDispatchObserver, FacilityDashboardObserver
from ..patterns.repository import InMemoryTelemetryRepository
from ..patterns.circuit_breaker import CircuitBreaker
from ..patterns.pipeline import EnergyTelemetryPipeline
from ..ml.anomaly_detector import EnergyAnomalyDetector

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="IoT-сервис потокового прогнозирования энергопотребления умных зданий и детекции аномальных пиков нагрузки"
)

# Инфраструктурные синглтоны
forecasting_strategy = XGBoostForecastingStrategy()
subject = EnergyAlertSubject()
dispatch_observer = OverloadDispatchObserver()
dashboard_observer = FacilityDashboardObserver()
subject.attach(dispatch_observer)
subject.attach(dashboard_observer)

repository = InMemoryTelemetryRepository()
circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_time_sec=5.0)
anomaly_detector = EnergyAnomalyDetector(residual_std=13.27, peak_limit_kw=settings.peak_overload_kw_threshold)

pipeline = EnergyTelemetryPipeline(
    strategy=forecasting_strategy,
    subject=subject,
    repository=repository,
    anomaly_detector=anomaly_detector
)

@app.post("/api/v1/energy/record", response_model=AnomalyAlert, tags=["Telemetry Ingestion"])
def record_telemetry(event: MeterReadingEvent):
    """Прием часового показания счетчика здания, расчет невязки и детекция аномалий."""
    try:
        alert = circuit_breaker.call(
            func=lambda: pipeline.execute(event),
            fallback=lambda: pipeline.execute(event)
        )
        return alert
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки телеметрии: {str(e)}")

@app.post("/api/v1/energy/forecast", response_model=EnergyForecastResponse, tags=["Forecasting"])
def forecast_energy(request: EnergyForecastRequest):
    """Прогноз часового энергопотребления здания на горизонт от 1 до 48 часов вперед."""
    start_time = time.time()
    history_24 = repository.get_recent_history(request.building_id, limit=24)
    current_power = history_24[-1] if history_24 else 350.0

    points, peak = forecasting_strategy.forecast_next_hours(
        current_kwh=current_power,
        start_hour=12,
        day_of_week=2,
        temp_c=request.forecast_temp_c or 20.0,
        humidity_pct=request.forecast_humidity or 50.0,
        horizon_hours=request.horizon_hours,
        history_24h=history_24
    )

    elapsed_ms = (time.time() - start_time) * 1000.0

    return EnergyForecastResponse(
        building_id=request.building_id,
        horizon_hours=request.horizon_hours,
        points=points,
        predicted_peak_kwh=peak,
        model_name=forecasting_strategy.name,
        latency_ms=round(elapsed_ms, 2)
    )

@app.get("/api/v1/energy/anomalies", response_model=List[AnomalyAlert], tags=["Analytics"])
def list_anomalies(limit: int = Query(50, ge=1, le=100)):
    """Список зафиксированных аварийных пиков и предупреждений."""
    return repository.list_anomalies(limit=limit)

@app.get("/api/v1/energy/stats/{building_id}", response_model=BuildingEnergyStats, tags=["Analytics"])
def get_building_stats(building_id: str):
    """Сводные метрики профиля энергопотребления здания."""
    return repository.get_building_stats(building_id)

@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Проверка состояния сервиса и предохранителя Circuit Breaker."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "circuit_breaker": circuit_breaker.state,
        "forecasting_model": forecasting_strategy.name,
        "environment": settings.environment
    }
