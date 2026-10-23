from abc import ABC, abstractmethod


class CarState(ABC):
    """Базовое состояние машины (State pattern)."""

    name: str = "base"

    @abstractmethod
    def update(self, car: "Car", dt: float) -> None:
        ...

    @abstractmethod
    def on_enter(self, car: "Car") -> None:
        ...

    def __repr__(self):
        return f"<CarState: {self.name}>"


class IdleState(CarState):
    name = "idle"

    def on_enter(self, car):
        car.accel = 0.0

    def update(self, car, dt):
        # Сопротивление катится
        car.speed *= 0.99
        if abs(car.speed) < 0.01:
            car.speed = 0.0
        if car.accel > 0.1:
            car.set_state(AcceleratingState())
        elif car.accel < -0.1:
            car.set_state(BrakingState())


class AcceleratingState(CarState):
    name = "accelerating"

    def on_enter(self, car):
        pass

    def update(self, car, dt):
        car.speed += car.accel * 10.0 * dt
        car.speed = min(car.speed, car.max_speed)
        if car.accel <= 0.1:
            car.set_state(IdleState() if car.accel > -0.1 else BrakingState())


class BrakingState(CarState):
    name = "braking"

    def on_enter(self, car):
        pass

    def update(self, car, dt):
        car.speed += car.accel * 15.0 * dt  # accel отрицательный
        car.speed = max(car.speed, 0.0)
        if car.accel >= -0.1:
            car.set_state(IdleState() if car.accel < 0.1 else AcceleratingState())


class CrashedState(CarState):
    name = "crashed"

    def on_enter(self, car):
        car.speed = 0.0
        car.accel = 0.0

    def update(self, car, dt):
        # Машина обездвижена
        car.speed = 0.0


class Car:
    """Модель автомобиля, использующая State pattern для смены режимов."""

    def __init__(self, x=0.0, y=0.0, angle=0.0):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 0.0
        self.accel = 0.0
        self.steer = 0.0
        self.max_speed = 50.0
        self._state: CarState = IdleState()
        self._state.on_enter(self)

    @property
    def state(self) -> CarState:
        return self._state

    def set_state(self, new_state: CarState):
        self._state = new_state
        self._state.on_enter(self)

    def crash(self):
        self.set_state(CrashedState())

    def update(self, dt: float = 0.1):
        self._state.update(self, dt)

        # Кинематика
        self.angle += self.steer * dt * (0.5 + abs(self.speed) * 0.02)
        self.x += self._cos(self.angle) * self.speed * dt
        self.y += self._sin(self.angle) * self.speed * dt

        # Сброс временных команд после шага
        self.accel = 0.0
        self.steer = 0.0

    @staticmethod
    def _cos(a):
        import math
        return math.cos(a)

    @staticmethod
    def _sin(a):
        import math
        return math.sin(a)

    def get_observation(self):
        return [self.x, self.y, self.angle, self.speed]

    def reset(self):
        self.x = 0.0
        self.y = 0.0
        self.angle = 0.0
        self.speed = 0.0
        self.accel = 0.0
        self.steer = 0.0
        self.set_state(IdleState())