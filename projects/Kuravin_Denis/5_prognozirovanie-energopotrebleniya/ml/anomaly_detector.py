from typing import Tuple
from ..models import AnomalySeverity, AnomalyAlert

class EnergyAnomalyDetector:
    """Детектор аномальных пиков и перегрузок энергопотребления (3-Sigma Residuals)."""

    def __init__(self, residual_std: float = 13.27, peak_limit_kw: float = 850.0):
        self.residual_std = max(1.0, residual_std)
        self.peak_limit_kw = peak_limit_kw

    def evaluate(
        self,
        building_id: str,
        actual_kwh: float,
        predicted_kwh: float,
        timestamp: float
    ) -> Tuple[AnomalySeverity, float, float, str]:
        residual = actual_kwh - predicted_kwh
        z_score = residual / self.residual_std

        # 1. Проверка на абсолютную перегрузку мощности вводного фидера
        if actual_kwh >= self.peak_limit_kw:
            severity = AnomalySeverity.CRITICAL_PEAK
            reason = (
                f"КРИТИЧЕСКАЯ ПЕРЕГРУЗКА: текущая мощность {actual_kwh:.1f} кВт превышает "
                f"проектный лимит подстанции ({self.peak_limit_kw:.1f} кВт)."
            )
            return severity, round(residual, 2), round(z_score, 2), reason

        # 2. Статистическая проверка по отклонению от прогноза ML (3-Sigma)
        if z_score >= 2.5:
            severity = AnomalySeverity.CRITICAL_PEAK
            reason = (
                f"Аномальный пиковый скачок: фактическое потребление {actual_kwh:.1f} кВт превышает "
                f"ожидаемый норматив ({predicted_kwh:.1f} кВт) на +{residual:.1f} кВт (Z={z_score:.1f} sigma)."
            )
        elif z_score >= 1.8:
            severity = AnomalySeverity.WARNING
            reason = (
                f"Повышенный расход энергии: отклонение +{residual:.1f} кВт выше нормы (Z={z_score:.1f} sigma)."
            )
        else:
            severity = AnomalySeverity.NORMAL
            reason = "Энергопотребление находится в пределах доверительного интервала модели."

        return severity, round(residual, 2), round(z_score, 2), reason
