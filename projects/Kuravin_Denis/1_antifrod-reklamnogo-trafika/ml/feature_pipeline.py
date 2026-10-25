import re
from datetime import datetime
from typing import Dict, Any
from ..models import ClickEvent

SUSPICIOUS_UA_PATTERNS = [
    r"python-requests",
    r"curl",
    r"wget",
    r"headlesschrome",
    r"phantomjs",
    r"selenium",
    r"puppeteer",
    r"bot",
    r"crawl",
    r"spider"
]

DATACENTER_IP_PREFIXES = [
    "104.", "185.", "194.", "45.", "193."  # Примеры префиксов хостингов/VPN/proxy
]

class FeaturePipeline:
    """Конвейер извлечения и нормализации признаков для антифрод-модели."""

    @staticmethod
    def extract_features(event: ClickEvent, ip_history_1min: int = 1, ip_history_5min: int = 1) -> Dict[str, float]:
        ua_lower = event.user_agent.lower()
        ua_bot_score = 1.0 if any(re.search(pat, ua_lower) for pat in SUSPICIOUS_UA_PATTERNS) else 0.0

        # Оценка подозрительности IP (датацентр / прокси)
        is_datacenter = 1.0 if any(event.ip_address.startswith(pfx) for pfx in DATACENTER_IP_PREFIXES) else 0.0

        # Временной интервал между показом и кликом (слишком малый < 200мс — признак скрипта)
        interval = float(event.click_interval_ms if event.click_interval_ms is not None else 1000)
        fast_click_flag = 1.0 if interval < 250.0 else 0.0

        # Несоответствие устройства и ОС
        device_lower = event.device_type.lower()
        os_lower = event.os.lower()
        device_mismatch = 1.0 if (device_lower == "mobile" and "windows" in os_lower) or (device_lower == "desktop" and "android" in os_lower) else 0.0

        dt = datetime.fromtimestamp(event.timestamp)
        hour = float(dt.hour)
        night_hours = 1.0 if 1 <= hour <= 5 else 0.0

        features = {
            "clicks_1min": float(ip_history_1min),
            "clicks_5min": float(ip_history_5min),
            "click_interval_ms": interval,
            "fast_click_flag": fast_click_flag,
            "ua_bot_score": ua_bot_score,
            "is_datacenter_ip": is_datacenter,
            "device_mismatch": device_mismatch,
            "night_hours": night_hours,
            "hour": hour
        }
        return features

    @staticmethod
    def feature_vector(features: Dict[str, float]) -> list:
        # Строгий порядок фичей для модели
        keys = [
            "clicks_1min",
            "clicks_5min",
            "click_interval_ms",
            "fast_click_flag",
            "ua_bot_score",
            "is_datacenter_ip",
            "device_mismatch",
            "night_hours",
            "hour"
        ]
        return [features[k] for k in keys]
