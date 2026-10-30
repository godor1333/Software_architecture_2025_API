# Дорожная сцена для БПЛА

Запускаемый учебный конвейер сегментации: он принимает PNG/JPEG по HTTP, строит цветовую маску пяти классов, сохраняет артефакты и метрики. Базовый сегментатор по цветовым признакам является воспроизводимой точкой сравнения для SegFormer/DeepLab. Production-профиль содержит адаптеры PyTorch/OpenCV/SegFormer, Kafka и MinIO; локальный запуск не требует скачивания весов.

```powershell
python app.py --demo
python app.py --evaluate
python app.py --integration-status
python app.py --serve --port 8012
python -m unittest -v
```

Для HTTP-запроса передайте изображение телом запроса и заголовки `X-Frame-Id`, `X-Flight-Id` в `POST /api/v1/frames`.

Для использования SegFormer задайте `SEGMENTATION_MODEL=nvidia/segformer-b0-finetuned-cityscapes-1024-1024`; при запросе к API будет выполняться модель. `python app.py --evaluate-road` сравнивает IoU дороги с цветовым методом на включённом кадре comma10k. Для запуска через FastAPI используйте `uvicorn api:api --host 127.0.0.1 --port 8012`.

Команда `python evaluate_comma10k.py` сравнивает модели на десяти включённых кадрах comma10k. Результат в `artifacts/comma10k_10_metrics.json`: среднее IoU дороги SegFormer 0,6923, цветового метода 0,2712; IoU разметки OpenCV 0,3365. Параметры OpenCV подбирались по первому кадру; выборка мала и не является независимой проверкой для всех условий движения.

Контейнер `worker` читает Kafka `frames.created`, получает исходный объект MinIO, выполняет сегментацию, сохраняет метаданные и маску и публикует `frames.segmented`. Пример события: `{"frame_id":"f2","flight_id":"flight1","bucket":"scene-frames","source_object":"frames/f1.png"}`. В исходной конфигурации используется цветовой метод; для SegFormer требуется задать `SEGMENTATION_MODEL` и доступ к весам в контейнере.

`artifacts/segmentation_metrics.json` содержит per-class IoU и mIoU на фиксированном контрольном кадре. Для SegFormer задайте `SEGMENTATION_MODEL`; при первом запуске веса загружаются из указанной модели.

В `services.yml` MinIO собирается из официального исходного тега `RELEASE.2024-10-13T13-34-11Z` через `Dockerfile.minio`. Это необходимо потому, что старый образ `minio/minio` и архив бинарника по этому тегу больше не публикуются; сборка закреплена по исходному тегу и не использует сторонний образ.

Дополнительная оценка `python evaluate_independent.py` использует 100 кадров comma10k из имён, оканчивающихся на 9.png; они не входят в первую десятку, использованную при подборе параметров. Среднее IoU дороги SegFormer 0,7521 против 0,2912 у цветового baseline; разметки OpenCV 0,3381. Объединённое по пикселям IoU дороги 0,7601 против 0,2853 у baseline, разметки 0,3703. Подробные результаты и SHA-256 файлов находятся в `artifacts/independent_metrics.json`. Кадры сняты автомобильной камерой; разделение по поездкам и пересечение с обучением SegFormer не установлены.

Для оценки вывода приложения дополнительно учитываются классы дороги и тротуара, а также наложение разметки. На тех же 100 кадрах среднее IoU итоговой маски: дорога 0,7667, разметка 0,3198, объединённые движущиеся объекты 0,3576; объединённое по пикселям IoU — 0,7705, 0,3395 и 0,4167 соответственно. Исходная метка движущихся объектов объединяет машины, людей и животных: отдельные оценки для машин и пешеходов здесь получить нельзя.

## Полный pipeline и аналитика

`FramePreprocessor` применяет EXIF-ориентацию, переводит кадр в RGB и ограничивает размер 1280×720. `SegmentationPipeline` объединяет preprocessing и Strategy, а `SceneAnalyticsObserver` записывает результат в `scene_analytics` с индексами `flight_id/captured_at` и `dominant_class`. Production-профиль дополнительно создаёт таблицу и индексы `scene_analytics` в PostgreSQL.

Для MP4-потока:

```powershell
python -X utf8 video_pipeline.py --demo --flight-id flight-demo --max-frames 8
python -X utf8 video_pipeline.py --input path\to\stream.mp4 --flight-id flight1 --api-url http://127.0.0.1:8012
```

При запущенном FastAPI доступны `GET /api/v1/analytics`, `GET /dashboard` и `GET /pipeline`. Реальные снимки запуска сохранены в `artifacts/dashboard_capture.png`, `artifacts/pipeline_capture.png` и `artifacts/api_docs_capture.png`.

Полные HTTP/Kafka-контракты находятся в `contracts/api_examples.md`, `contracts/frames.created.json` и `contracts/frames.segmented.json`. C4 Context/Component исходники и PNG находятся в `diagrams/p2_c4_context.*` и `diagrams/p2_c4_component.*`.

## Проверка на кадрах БПЛА

В `data/uavid/README.md` описано подключение официального UAVid. После размещения внешних `Images/*.png` и `Labels/*.png` команда `python -X utf8 evaluate_uavid.py --data-dir data/uavid --limit 100` вычисляет отдельные pooled IoU для дороги, машин и людей. Файлы UAVid не включены в архив из-за лицензии и размера; до загрузки датасета UAV-метрики считаются неподтверждёнными.
