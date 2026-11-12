"""Единая настройка логирования для всех сервисов."""
import logging


def setup(level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    return logging.getLogger("pong")
