import time
from enum import Enum
from typing import Callable, Any, Optional

class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Нормальное состояние: запросы проходят
    OPEN = "OPEN"          # Цепь разорвана: запросы отклоняются сразу
    HALF_OPEN = "HALF_OPEN"# Пробное состояние: проверка восстановления

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    """Паттерн Circuit Breaker для предотвращения каскадных сбоев."""

    def __init__(self, failure_threshold: int = 3, recovery_time_sec: float = 10.0):
        self.failure_threshold = failure_threshold
        self.recovery_time_sec = recovery_time_sec
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

    def call(self, func: Callable, fallback: Optional[Callable] = None, *args, **kwargs) -> Any:
        now = time.time()

        if self.state == CircuitState.OPEN:
            if now - self.last_state_change > self.recovery_time_sec:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
            else:
                if fallback:
                    return fallback(*args, **kwargs)
                raise CircuitBreakerOpenException("Circuit Breaker is OPEN. Call rejected.")

        try:
            result = func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                # Успешный пробный вызов восстанавливает состояние
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_state_change = now
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = now
            if fallback:
                return fallback(*args, **kwargs)
            raise e
