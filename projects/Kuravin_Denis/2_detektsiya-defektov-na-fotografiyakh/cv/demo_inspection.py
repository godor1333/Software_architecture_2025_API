import os
import cv2
import numpy as np
from ..patterns.factory import DetectorFactory
from ..patterns.adapter import LocalFallbackStorageAdapter
from ..patterns.repository import InMemoryReportRepository
from ..patterns.pipeline import CarDamagePipeline, PipelineContext

def generate_sample_damaged_car_image() -> bytes:
    """Генерирует тестовое синтетическое фото детали автомобиля (крыло / дверь) с царапиной и вмятиной."""
    # Металлик серый фон кузова
    img = np.full((720, 1080, 3), (120, 125, 130), dtype=np.uint8)

    # Добавляем градиент блика на лаке
    img_float = img.astype(np.float32)
    for y in range(720):
        img_float[y, :, :] += (y - 360) * 0.12
    img = np.clip(img_float, 0, 255).astype(np.uint8)

    # 1. Рисуем выраженную царапину (белая ломаная линия с темной тенью)
    pts = np.array([[240, 280], [380, 310], [450, 290], [580, 340]], np.int32)
    cv2.polylines(img, [pts], False, (240, 240, 240), 4, cv2.LINE_AA)
    cv2.polylines(img, [pts + 2], False, (40, 40, 40), 2, cv2.LINE_AA)

    # 2. Рисуем вмятину (овальная радиальная зона затемнения/деформации)
    cv2.ellipse(img, (750, 420), (140, 80), 25, 0, 360, (65, 70, 75), -1)
    cv2.ellipse(img, (750, 420), (140, 80), 25, 0, 360, (35, 40, 45), 3)

    _, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    return encoded.tobytes()

def run_demo():
    print("=" * 70)
    print("  ДЕМОНСТРАЦИЯ: ДЕТЕКЦИЯ ДЕФЕКТОВ АВТОМОБИЛЯ (CV PIPELINE)")
    print("=" * 70)

    raw_bytes = generate_sample_damaged_car_image()
    print(f"Сгенерировано тестовое фото кузова (размер: {len(raw_bytes):,} байт)")

    strategy = DetectorFactory.get_detector("yolov8_fast")
    storage = LocalFallbackStorageAdapter(base_dir="project_2_car_damage_detection/storage_uploads")
    repo = InMemoryReportRepository()

    pipeline = CarDamagePipeline(
        detector_strategy=strategy,
        storage_adapter=storage,
        report_repository=repo
    )

    ctx = PipelineContext(
        raw_bytes=raw_bytes,
        vehicle_vin="XTA2109301294819",
        client_id="alfa_insurance_auto"
    )

    report = pipeline.execute(ctx)

    print("\n" + "-" * 70)
    print(f"  ОТЧЕТ ОБ ИНСПЕКЦИИ: {report.report_id}")
    print("-" * 70)
    print(f"VIN автомобиля:             {report.vehicle_vin}")
    print(f"Клиент / Страховая:         {report.client_id}")
    print(f"Использованная модель:      {report.model_name}")
    print(f"Время обработки (Latency):  {report.processing_time_ms:.2f} ms")
    print(f"Общая тяжесть повреждений:  {report.overall_severity.value.upper()}")
    print(f"Количество дефектов:        {report.total_damages_count}")
    print(f"Предварительная смета:      {report.total_estimated_repair_rub:,.2f} RUB")
    print("\nОбнаруженные дефекты:")
    for idx, d in enumerate(report.damages, 1):
        print(f"  [{idx}] {d.damage_type.value.upper():<16} Уверенность: {d.confidence:.1%} | BBox: ({d.x_min}, {d.y_min}) -> ({d.x_max}, {d.y_max}) | Оценка ремонта: {d.estimated_repair_rub:,.0f} RUB")

    print("\nURL размеченного фото:      ", report.annotated_image_url)
    print("=" * 70)

if __name__ == "__main__":
    run_demo()
