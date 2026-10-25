import os
import joblib
from typing import Tuple, Dict
from ..models import ClickEvent
from .feature_pipeline import FeaturePipeline

class MLFraudScorer:
    """Сервис инференса обученной XGBoost-модели антифрода."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLFraudScorer, cls).__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "model.joblib")
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            self.model = None

    def score(self, event: ClickEvent, ip_history_1min: int = 1, ip_history_5min: int = 1) -> Tuple[float, Dict[str, float]]:
        features = FeaturePipeline.extract_features(event, ip_history_1min, ip_history_5min)
        if self.model is None:
            # Fallback эвристический скор, если модель не загружена
            score = 0.1
            if features["fast_click_flag"] == 1.0:
                score += 0.35
            if features["ua_bot_score"] == 1.0:
                score += 0.4
            if features["clicks_1min"] > 10:
                score += 0.3
            return min(1.0, score), features

        vec = FeaturePipeline.feature_vector(features)
        proba = float(self.model.predict_proba([vec])[0][1])
        return proba, features
