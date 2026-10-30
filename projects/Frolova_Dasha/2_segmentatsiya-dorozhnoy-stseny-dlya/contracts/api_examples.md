# Контракты API и сообщений

## HTTP

- `POST /api/v1/frames` принимает PNG/JPEG в теле запроса и заголовки `X-Frame-Id`, `X-Flight-Id`. Ответ `201` содержит `frame_id`, `flight_id`, размеры нормализованного кадра, имя маски, `class_share`, `dominant_class`, время и параметры preprocessing.
- `GET /api/v1/frames/{frame_id}` возвращает сохранённую сегментацию.
- `GET /api/v1/summary` возвращает число кадров, полётов и распределение доминирующих классов.
- `GET /api/v1/analytics?flight_id=...` возвращает записи аналитики по полёту.
- `GET /dashboard?flight_id=...` показывает dashboard.
- `GET /pipeline?flight_id=...` показывает поток video stream → preprocessing → segmentation → analytics → Kafka/dashboard.

## Kafka

Полные примеры JSON находятся в `frames.created.json` и `frames.segmented.json`. Ключом сообщения является `frame_id`. Worker читает `frames.created`, получает объект из MinIO, запускает pipeline, записывает метаданные в PostgreSQL и публикует `frames.segmented`. API также публикует `frames.segmented` после синхронной записи production-артефактов.
