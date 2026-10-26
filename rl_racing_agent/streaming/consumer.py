<<<<<<< HEAD
import json
from kafka import KafkaConsumer
from .events import TelemetryEvent


class TelemetryConsumer:
    def __init__(self, bootstrap_servers="localhost:9092", topic="racing-telemetry", group_id="telemetry-group"):
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
        )

    def __iter__(self):
        for msg in self.consumer:
=======
import json
from kafka import KafkaConsumer
from .events import TelemetryEvent


class TelemetryConsumer:
    def __init__(self, bootstrap_servers="localhost:9092", topic="racing-telemetry", group_id="telemetry-group"):
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
        )

    def __iter__(self):
        for msg in self.consumer:
>>>>>>> 0037982a52b70d8ed1ac0df57ec0f7ee8fcf872b
            yield TelemetryEvent(**msg.value)