import cv2
import numpy as np
from typing import List, Tuple, Dict, Any
from ..models import DamageBoundingBox, DamageClass, SeverityLevel

# Базовые тарифы на ремонтные работы (в рублях)
BASE_REPAIR_COSTS = {
    DamageClass.SCRATCH: {"base": 4500.0, "factor_area": 0.05},
    DamageClass.DENT: {"base": 8500.0, "factor_area": 0.08},
    DamageClass.BROKEN_HEADLIGHT: {"base": 24000.0, "factor_area": 0.12},
    DamageClass.CRACKED_GLASS: {"base": 16000.0, "factor_area": 0.07},
    DamageClass.BUMPER_DAMAGE: {"base": 14000.0, "factor_area": 0.09}
}

CLASS_COLORS = {
    DamageClass.SCRATCH: (0, 255, 255),          # Желтый
    DamageClass.DENT: (0, 165, 255),             # Оранжевый
    DamageClass.BROKEN_HEADLIGHT: (0, 0, 255),   # Красный
    DamageClass.CRACKED_GLASS: (255, 0, 255),    # Фиолетовый
    DamageClass.BUMPER_DAMAGE: (255, 100, 0)     # Сине-голубой
}

class DamageInferenceEngine:
    """Движок детекции дефектов и оценки восстановительной стоимости."""

    def __init__(self, confidence_threshold: float = 0.40):
        self.conf_threshold = confidence_threshold

    def calculate_nms(self, boxes: List[DamageBoundingBox], iou_threshold: float = 0.5) -> List[DamageBoundingBox]:
        """Non-Maximum Suppression для устранения перекрывающихся детекций."""
        if not boxes:
            return []

        # Преобразуем в массив [x1, y1, x2, y2, score]
        rects = np.array([[b.x_min, b.y_min, b.x_max, b.y_max] for b in boxes], dtype=float)
        scores = np.array([b.confidence for b in boxes], dtype=float)

        x1 = rects[:, 0]
        y1 = rects[:, 1]
        x2 = rects[:, 2]
        y2 = rects[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(ovr <= iou_threshold)[0]
            order = order[inds + 1]

        return [boxes[k] for k in keep]

    def estimate_repair(self, damage_type: DamageClass, width: int, height: int) -> Tuple[SeverityLevel, float]:
        area = width * height
        cost_cfg = BASE_REPAIR_COSTS[damage_type]
        repair_cost = cost_cfg["base"] + (area * cost_cfg["factor_area"])

        if area < 5000 and damage_type in [DamageClass.SCRATCH, DamageClass.DENT]:
            severity = SeverityLevel.MINOR
        elif area < 25000 or damage_type in [DamageClass.BUMPER_DAMAGE, DamageClass.CRACKED_GLASS]:
            severity = SeverityLevel.MODERATE
        else:
            severity = SeverityLevel.SEVERE
            repair_cost *= 1.3

        return severity, round(repair_cost, 2)

    def annotate_image(self, original_bgr: np.ndarray, damages: List[DamageBoundingBox]) -> np.ndarray:
        """Отрисовывает bounding box'ы, класс, уверенность и стоимость ремонта на изображении."""
        annotated = original_bgr.copy()
        h, w = annotated.shape[:2]

        for d in damages:
            color = CLASS_COLORS.get(d.damage_type, (0, 255, 0))
            x1 = max(0, min(w - 1, d.x_min))
            y1 = max(0, min(h - 1, d.y_min))
            x2 = max(0, min(w - 1, d.x_max))
            y2 = max(0, min(h - 1, d.y_max))

            # Рамка дефекта
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)

            # Подложка под текст
            label = f"{d.damage_type.value} {d.confidence:.0%} (~{int(d.estimated_repair_rub):,} RUB)"
            (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(annotated, (x1, max(0, y1 - th - 10)), (x1 + tw + 6, y1), color, -1)
            cv2.putText(
                annotated,
                label,
                (x1 + 3, max(th + 2, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 0),
                2,
                cv2.LINE_AA
            )

        return annotated
