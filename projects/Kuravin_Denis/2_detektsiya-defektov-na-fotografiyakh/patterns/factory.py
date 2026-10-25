from typing import Dict, Type
from .strategy import IDamageDetectorStrategy, FastYOLOv8Strategy, HighAccuracyMaskRCNNStrategy

class DetectorFactory:
    """Паттерн Фабрика (Factory Pattern) для создания стратегий детекции."""

    _registry: Dict[str, Type[IDamageDetectorStrategy]] = {
        "yolov8_fast": FastYOLOv8Strategy,
        "mask_rcnn_deep": HighAccuracyMaskRCNNStrategy
    }

    @classmethod
    def get_detector(cls, strategy_name: str = "yolov8_fast", **kwargs) -> IDamageDetectorStrategy:
        strategy_class = cls._registry.get(strategy_name.lower())
        if not strategy_class:
            valid_keys = ", ".join(cls._registry.keys())
            raise ValueError(f"Неизвестная стратегия детекции: '{strategy_name}'. Допустимые: {valid_keys}")
        return strategy_class(**kwargs)

    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[IDamageDetectorStrategy]) -> None:
        cls._registry[name.lower()] = strategy_class
