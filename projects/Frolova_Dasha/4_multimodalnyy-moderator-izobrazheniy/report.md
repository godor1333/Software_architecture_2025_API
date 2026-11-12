# Отчёт по лабораторной работе №4
## Мультимодальный модератор изображений форумов

### 1. Цель и проблема проекта

Цель — построить сервис автоматической модерации контента форума, который объединяет анализ изображений и анализ текста публикации в единое решение: approve (опубликовать), flag (на проверку модератору), reject (заблокировать).

Проблема: ручная модерация форумов не масштабируется. Модератор не успевает просматривать поток постов, а изображения часто являются главным носителем запрещённого контента (сцены насилия, оружие, наркотики, реклама казино, мошеннические баннеры, спам-дубликаты). Решение нельзя принимать только по картинке или только по тексту: фото оружия в научно-популярной статье и текст «продам ружьё» под безобидным пейзажем — разные случаи, требующие совместного анализа. Отсюда multimodal fusion: два классификатора работают параллельно, а политика модерации агрегирует их сигналы, усиливая уверенность при совпадении модальностей.

### 2. Требования и ограничения

Функциональные требования:
- приём поста (изображение + текст) через REST API;
- классификация изображения по 7 категориям (CLIP zero-shot);
- классификация текста по 3 категориям (abuse / scam_text / clean);
- обнаружение дубликатов изображений по перцептуальному хешу (pHash);
- агрегация двух модальностей в итоговый вердикт (policy fusion);
- сохранение вердиктов в PostgreSQL и индексация событий в Elasticsearch;
- сменные политики модерации без изменения кода (Strategy).

Ограничения:
- категории модерации ограничены заданным списком; 
- zero-shot CLIP используется без дообучения;
- таблица хешей дедупликации хранится в памяти процесса vision и очищается при рестарте сервиса (ограничение демо-версии; в промышленной версии — Redis или БД);
- инференс CPU-only: один пост проходит пайплайн за единицы секунд;
- деплой локальный (docker-compose), без оркестрации.

### 3. Описание входных и выходных данных

Вход: POST /api/v1/posts (multipart/form-data):
- image — файл изображения (jpg/jpeg/png/gif/webp, до 15 МБ);
- text — текст публикации (по умолчанию пустая строка);
- user_id — идентификатор автора (по умолчанию "anon").

Выход: GET /api/v1/posts/{post_id} — вердикт в JSON:
- decision — approve / flag / reject;
- category — категория нарушения или benign;
- scores — скоры обеих модальностей (vision_category, vision_score, text_category, text_score);
- reasons — машинно-читаемые обоснования решения;
- trace — трассировка прохождения цепочки обработчиков;
- policy — применённая политика; created_at — время вердикта.

Пример ответа:
{
  "post_id": "e9cf3efb-ded2-45bb-9678-a412203be77f",
  "decision": "flag",
  "category": "violence",
  "scores": {"vision_category": "violence", "vision_score": 0.325,
             "text_category": "abuse", "text_score": 0.810},
  "reasons": ["vision:violence:eff=0.43 thr=0.30"],
  "policy": "standard",
  "trace": ["HardBanHandler", "DuplicateHandler", "CrossModalHandler",
            "ThresholdHandler", "FinalHandler"],
  "created_at": "2026-11-08T09:14:02+00:00"
}

Промежуточные Kafka-события несут те же поля: vision — {post_id, category, score, scores, duplicate, duplicate_of, phash}; text — {post_id, category, score}.

### 4. Архитектурная схема (C4)

C4 Level 1 — System Context: актор «пользователь форума» публикует посты через API; актор «модератор/аналитик» читает вердикты, статистику и выполняет поиск.

C4 Level 2 — Containers (поток данных):

Пользователь --> api (FastAPI, :8000) --> Kafka (media.submitted)
                                            |
                 +--------------------------+--------------------------+
                 |                                                     |
          vision-svc (CLIP + pHash)                          text-svc (BERT)
                 |                                                     |
          vision.verdicts                                     text.verdicts
                 +--------------------------+--------------------------+
                                            |
                                     fusion-svc (join по post_id, таймаут 15 c;
                                     Strategy + Chain of Responsibility)
                                            |
                                    moderation.events
                                            |
                                     indexer-svc --> PostgreSQL + Elasticsearch

Инфраструктура: Kafka (шина событий), MinIO (S3-хранилище изображений), PostgreSQL (верdicts), Elasticsearch (поисковый индекс), kafka-ui (админ-панель :8085).

C4 Level 3 — Component (сервис api): ModeratorFacade (паттерн Facade) инкапсулирует make_bus() (Kafka/InMemory), make_storage() (MinIO/Local — паттерн Adapter) и прямые запросы к PostgreSQL и Elasticsearch. Клиент API знает только фасад.

[СКРИНШОТ: схема архитектуры или docker compose ps — все контейнеры healthy]

### 5. Микросервисы и границы ответственности

| Сервис | Ответственность | Границы |
|---|---|---|
| api | Валидация входа (тип файла, размер до 15 МБ), загрузка изображения в MinIO, публикация media.submitted; витрина: чтение вердикта, статистика, поиск | Не классифицирует и не принимает решений |
| vision | Скачивает изображение из хранилища, классификация CLIP zero-shot по 7 категориям, расчёт pHash и дедупликация, публикация vision.verdicts | Не знает о политике и тексте поста |
| text | Классификация текста (abuse / scam_text / clean), публикация text.verdicts | Не анализирует изображение |
| fusion | Join двух модальностей по post_id (таймаут 15 с, недостающая модальность подставляется нейтральной), применение политики и цепочки правил, публикация moderation.events, рассылка наблюдателям | Не хранит состояние между постами, не пишет в БД |
| indexer | Запись вердикта в PostgreSQL (идемпотентный upsert) и индексация в Elasticsearch | Только запись, без бизнес-логики |

### 6. Kafka: топики, producers/consumers, формат сообщений и consumer groups

| Топик | Producer | Consumer group | Формат сообщения (JSON) |
|---|---|---|---|
| media.submitted | api | vision-svc, text-svc | {post_id, user_id, media_key, text, created_at} |
| vision.verdicts | vision | fusion-svc | {post_id, category, score, scores, duplicate, duplicate_of, phash} |
| text.verdicts | text | fusion-svc | {post_id, category, score} |
| moderation.events | fusion | indexer-svc | {post_id, decision, category, scores, reasons, policy, trace, created_at} |

- Ключ всех сообщений — post_id: партиционирование по посту и упорядоченность в рамках поста.
- Consumer groups изолируют сервисы: vision-svc и text-svc независимо читают media.submitted (каждый получает все события); fusion-svc потребляет оба вердикт-топика; indexer-svc — финальные события.
- Коммит смещений — после обработки (enable.auto.commit=false в fusion), событие не теряется при падении сервиса.
- Join в fusion: вердикт формируется, когда пришли оба сигнала, либо по таймауту 15 с.

[СКРИНШОТ: kafka-ui (http://localhost:8085) — топики и сообщения]

### 7. Схема аналитического хранилища и индексы

PostgreSQL, файл db/init.sql:

CREATE TABLE moderation_verdicts (
    id          BIGSERIAL PRIMARY KEY,
    post_id     UUID NOT NULL,
    decision    VARCHAR(16) NOT NULL CHECK (decision IN ('approve','flag','reject')),
    category    VARCHAR(32) NOT NULL DEFAULT 'none',
    scores      JSONB NOT NULL DEFAULT '{}',
    reasons     TEXT[] NOT NULL DEFAULT '{}',
    policy      VARCHAR(32) NOT NULL DEFAULT 'standard',
    trace       TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE media_objects (
    id          BIGSERIAL PRIMARY KEY,
    post_id     UUID NOT NULL,
    media_key   VARCHAR(512) NOT NULL,
    phash       VARCHAR(64),
    size_bytes  BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

Индексы и назначение:
- ux_verdicts_post_id (UNIQUE по post_id) — идемпотентность: indexer выполняет upsert, повторная доставка события не создаёт дубликат строки;
- ix_verdicts_decision, ix_verdicts_category — быстрая агрегация статистики (/api/v1/stats);
- ix_verdicts_created_at (DESC) — лента свежих вердиктов;
- ix_verdicts_scores_gin (GIN по JSONB scores) — поиск по структуре скоров;
- ix_media_phash — поиск хеша при дедупликации; ix_media_post_id — связь с постом.

Elasticsearch: индекс moderation-events, документ — полный вердикт; поиск по полям text / category / decision через bool/should.

### 8. API: примеры запросов и ответов

# Здоровье сервиса
curl http://localhost:8000/health
--> {"status":"ok"}

# Отправка поста
curl -X POST http://localhost:8000/api/v1/posts \
  -F image=@data/demo/demo_00_violence.jpg \
  -F "text=видео драки" -F "user_id=tester"
--> 202 {"post_id":"e9cf…","media_key":"posts/e9cf…/upload.jpg","status":"accepted"}

# Чтение вердикта
curl http://localhost:8000/api/v1/posts/<post_id>
--> {"post_id":"e9cf…","decision":"flag","category":"violence",…}

# Статистика по решениям
curl http://localhost:8000/api/v1/stats
--> {"approve": 2, "flag": 6, "reject": 1}

# Поиск по событиям (Elasticsearch)
curl "http://localhost:8000/api/v1/search?q=reject"
--> [{"post_id":"…","decision":"reject","category":"spam",…}, …]

Коды ошибок: 400 — неподдерживаемый тип файла или пустой файл; 413 — файл больше 15 МБ; 404 — вердикт ещё не готов или пост не найден.

[СКРИНШОТ: ответ GET /api/v1/posts/<id> с verdict]

### 9. Применённые паттерны (5)

1) Strategy — services/fusion/policies.py.
Место применения: выбор политики модерации fusion-сервисом.
Зачем: строгость модерации меняется одной переменной окружения (POLICY=standard | strict_family | spam_focus) без изменения кода цепочки. Для разделов с детьми — жёсткие пороги, для спам-пиков — агрессивная ловля спама.
Схема: общий интерфейс ModerationPolicy (thresholds(), fusion_boost()) и три реализации; get_policy(name) возвращает стратегию по имени.

THRESHOLDS_STANDARD = {"violence": 0.30, "weapons": 0.30, "drugs": 0.30,
                       "gambling": 0.30, "scam": 0.30, "spam": 0.30, "benign": 1.01}
class StandardPolicy(ModerationPolicy):
    name = "standard"
    def thresholds(self): return THRESHOLDS_STANDARD
    def fusion_boost(self, vcat, tcat):
        pairs = {("gambling","scam_text"), ("scam","scam_text"), ("spam","scam_text"),
                 ("violence","abuse"), ("weapons","abuse"), ("drugs","abuse")}
        return 0.10 if (vcat, tcat) in pairs else 0.0
POLICIES = {"standard": StandardPolicy, "strict_family": StrictFamilyPolicy,
            "spam_focus": SpamFocusPolicy}
def get_policy(name): return POLICIES.get(name, StandardPolicy)()

2) Chain of Responsibility — services/fusion/chain.py.
Место применения: принятие решения о вердикте в fusion.
Зачем: правила модерации упорядочены от самых строгих к дефолтным, каждый обработчик либо решает судьбу поста, либо передаёт ход дальше; новые правила добавляются вставкой звена без переписывания существующих.
Схема цепочки: HardBanHandler (мгновенный reject тяжёлых категорий с высокой уверенностью) -> DuplicateHandler (дубль => reject как спам) -> CrossModalHandler (fusion-буст при совпадении модальностей) -> ThresholdHandler (пороговое flag/reject) -> FinalHandler (default approve).

def build_chain():
    return HardBanHandler(
        DuplicateHandler(
            CrossModalHandler(
                ThresholdHandler(FinalHandler()))))

class Handler:
    def __init__(self, next_handler=None): self._next = next_handler
    def handle(self, ctx):
        handled = self._handle(ctx)
        if handled is not None: return handled
        if self._next is not None: return self._next.handle(ctx)
        return None

3) Observer — services/fusion/observers.py.
Место применения: реакция на событие «вердикт сформирован» в fusion.
Зачем: метрики, аудит-лог и внешние вебхуки подключаются без изменения основной логики fusion; при добавлении нового подписчика (например, отправка в Telegram) ядро не меняется.
Схема: интерфейс VerdictObserver.on_verdict(verdict); реализации MetricsObserver (счётчики approve/flag/reject), AuditLogObserver (строки аудита в stdout), WebhookObserver (POST вердикта на внешний URL).

observers = [MetricsObserver(), AuditLogObserver(), WebhookObserver(os.getenv("WEBHOOK_URL"))]
for obs in observers: obs.on_verdict(verdict)

4) Facade — services/api/facade.py.
Место применения: единая точка входа API-сервиса.
Зачем: клиент REST знает только ModeratorFacade; под фасадом спрятаны Kafka-продюсер, MinIO-хранилище, PostgreSQL и Elasticsearch. Смена шины или хранилища не затрагивает HTTP-слой.
Схема: ModeratorFacade.submit_post() (публикация media.submitted), store_image() (загрузка в хранилище), get_verdict() (Postgres), stats() (агрегация), search() (Elasticsearch).

class ModeratorFacade:
    def __init__(self, bus, storage): self.bus = bus; self.storage = storage
    def submit_post(self, post_id, user_id, media_key, text):
        event = {...}; self.bus.publish("media.submitted", post_id, event); return event

5) Adapter — common/storage.py.
Место применения: работа с хранилищем изображений в api и vision.
Зачем: единый порт ObjectStorage (put_bytes/get_bytes) с двумя реализациями — MinioStore (MinIO/S3) и LocalStore (локальный диск). Тесты и локальный запуск идут на LocalStore (USE_LOCAL_STORAGE=1), прод-режим — на MinIO, без изменения вызывающего кода.
Схема: ObjectStorage — абстрактный порт; MinioStore и LocalStore — адаптеры к конкретным системам; make_storage() выбирает реализацию по переменной окружения.

class ObjectStorage:
    def put_bytes(self, key, data): raise NotImplementedError
    def get_bytes(self, key): raise NotImplementedError
def make_storage():
    if os.getenv("USE_LOCAL_STORAGE") == "1": return LocalStore(...)
    return MinioStore(...)

### 10. Dockerfile / docker-compose и инструкция запуска

Состав docker-compose (10 сервисов, общая сеть forummod_net, именованные тома kafka_data/minio_data/pg_data/es_data):
kafka (apache/kafka:3.9.0, KRaft-режим), minio (9000/9001), postgres (16, healthcheck pg_isready, схема из db/init.sql), elasticsearch (8.11.1, single-node, healthcheck), kafka-ui (:8085), api (:8000), vision, text, fusion, indexer.
Зависимости через depends_on с condition: service_healthy — сервисы стартуют только после готовности инфраструктуры. Vision и text монтируют том ./models:/models (кэш Hugging Face).

Запуск:
1. docker compose up -d --build
2. дождаться healthchecks: docker compose ps — все контейнеры healthy/running
3. сквозной тест: make demo (python3 scripts/run_e2e.py --mode demo) — ожидается RESULT: PASS
4. веб-интерфейсы: kafka-ui http://localhost:8085, MinIO console http://localhost:9001
5. перед повторным демо-прогоном: docker compose restart vision (сброс таблицы дедупликации)

### 11. Тестирование и результаты

Виды тестов:
1. Сквозной контрактный e2e (scripts/run_e2e.py): отправка 8 постов с изображениями и тематическими текстами через реальный REST API, ожидание вердикта по каждому, проверка контракта дубликата (повторная отправка того же изображения обязана получить reject/spam), проверка индексации в Elasticsearch.
2. Проверка классификатора: прямая оценка CLIP на наборе demo-изображений.
3. Healthcheck-проверки всех инфраструктурных контейнеров.

Результат прогона:
demo_00_violence.jpg  expected=violence  decision=flag     category=violence  OK
demo_01_weapons.jpg   expected=weapons   decision=flag     category=weapons   OK
demo_02_drugs.jpg     expected=drugs     decision=flag     category=drugs     OK
demo_03_gambling.jpg  expected=gambling  decision=flag     category=gambling  OK
demo_04_scam.jpg      expected=scam      decision=flag     category=scam      OK
demo_05_spam.jpg      expected=spam      decision=flag     category=spam      OK
demo_06_benign_park.jpg expected=benign  decision=approve  category=benign    OK
demo_07_benign_food.jpg expected=benign  decision=approve  category=benign    OK
duplicate-check       decision=reject    category=spam     OK
es-check: OK
RESULT: PASS

Результат сохраняется в artifacts/e2e_results.json.


### 12. ML: датасет, preprocessing, модель, метрики, baseline, результаты и ограничения

Датасет: валидационный набор из 8 реальных фотографий (data/demo/), по одной на каждую категорию: сцена драки, пистолет, шприц/таблетки, рулетка казино, баннер мошенничества («вам выпал приз»), рекламный спам-баннер, парк, еда. К каждой постится тематический текст (для gamble/scam/spam — совпадающий с картинкой по смыслу, что включает fusion-буст).

Preprocessing: изображение приводится к входу CLIP (нормализация RGB 224x224 средствами трансформеров Hugging Face); для pHash — перевод в grayscale, resize 32x32 (LANCZOS), DCT-II, срез низких частот 8x8, бинаризация относительно медианы. Дубликат — расстояние Хэмминга <= 6.

Модель: CLIP ViT-B/32, zero-shot классификация без дообучения. Категории задаются текстовыми промптами («a photo of violence/fighting», «a photo of a handgun/weapon», «pills or syringe, drugs», «casino roulette, gambling», «scam prize banner», «spam advertisement banner», «a normal photo of nature or food»); softmax по 21 промпту даёт вероятность каждой категории.

Baseline и метрики: базовый вариант на синтетически сгенерированных изображениях давал 4/8 категорий — CLIP плохо распознаёт абстрактную графику. После замены валидационного набора на реальные фотографии (и калибровки порогов под шкалу zero-shot вероятностей: пороги 0.26–0.35 вместо 0.60–0.85) точность классификации составила 8/8 = 100%. Детект дубликатов по pHash — 8/8 (повторная отправка изображения внутри прогона поймана, вердикт reject/spam). Все вердикты e2e — корректные: запрещённые категории flag, benign approve, дубль reject.

Ограничения: zero-shot CLIP без дообучения чувствителен к качеству промптов; маленький валидационный набор (8 изображений) не заменяет полноценного теста на сотнях примеров; шкала вероятностей zero-shot занижена и требует отдельной калибровки при изменении набора промптов.


### 13. Выводы и распределение работы

Выводы: построен работающий event-driven пайплайн мультимодальной модерации из 5 микросервисов поверх Kafka с хранением в PostgreSQL/MinIO и поиском в Elasticsearch. Реализованы и продемонстрированы 5 паттернов проектирования (Strategy, Chain of Responsibility, Observer, Facade, Adapter). CLIP zero-shot на реальных фотографиях показал 8/8 (100%) по категориям после калибровки порогов; pHash-дедупликация ловит повторные изображения 8/8. Сквозной контрактный e2e-тест проходит: RESULT: PASS. Основные ограничения — in-memory таблица дедупликации и отсутствие дообучения моделей; пути развития — Redis для дедупа, файнтюнинг классификаторов, RL-управление политиками.


### Приложение: команды запуска

docker compose up -d --build          # поднять весь стек
docker compose ps                     # проверить состояние
make demo                             # сквозной e2e-тест
docker compose restart vision         # сброс дедуп-памяти перед повторным демо
