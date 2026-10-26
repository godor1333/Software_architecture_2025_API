<<<<<<< HEAD
import json
from kafka import KafkaProducer
from .events import TelemetryEvent


class TelemetryProducer:
    def __init__(self, bootstrap_servers="localhost:9092", topic="racing-telemetry"):
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def send(self, event: TelemetryEvent):
        self.producer.send(self.topic, event.to_dict())

    def flush(self):
        self.producer.flush()

    def close(self):
=======
import json
from kafka import KafkaProducer
from .events import TelemetryEvent


class TelemetryProducer:
    def __init__(self, bootstrap_servers="localhost:9092", topic="racing-telemetry"):
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def send(self, event: TelemetryEvent):
        self.producer.send(self.topic, event.to_dict())

    def flush(self):
        self.producer.flush()

    def close(self):
>>>>>>> 0037982a52b70d8ed1ac0df57ec0f7ee8fcf872b
        self.producer.close()