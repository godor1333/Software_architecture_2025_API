# Паттерн Adapter: единый порт MessageBus + реализации Kafka и InMemory
import json

class MessageBus:  # Порт (интерфейс адаптера)
    def publish(self, topic, key, value):
        raise NotImplementedError
    def subscribe(self, topic, queue):
        raise NotImplementedError

class KafkaBus(MessageBus):
    def __init__(self, bootstrap):
        from confluent_kafka import Producer
        self._p = Producer({"bootstrap.servers": bootstrap})

    def publish(self, topic, key, value):
        self._p.produce(topic, key=str(key).encode(),
                        value=json.dumps(value, ensure_ascii=False).encode())
        self._p.poll(0)

    def flush(self):
        self._p.flush(5)

    def subscribe(self, topic, queue):  # в Kafka-режиме не используется
        raise RuntimeError("KafkaBus: используйте ConsumerLoop")

class InMemoryBus(MessageBus):
    # Реализация для юнит-тестов: без брокера
    def __init__(self):
        self._subs = {}
        self.published = []

    def publish(self, topic, key, value):
        self.published.append((topic, key, value))
        for q in self._subs.get(topic, []):
            q.put((key, value))

    def subscribe(self, topic, queue):
        self._subs.setdefault(topic, []).append(queue)

def make_bus():
    import os
    if os.getenv("USE_INMEMORY_BUS") == "1":
        return InMemoryBus()
    return KafkaBus(os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"))
