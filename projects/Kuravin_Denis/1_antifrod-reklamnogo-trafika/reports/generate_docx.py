import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def generate_report():
    doc = Document()

    # Поля страницы
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Титульный блок
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = title.add_run("ОТЧЁТ ПО ПРОЕКТУ №1\n«Антифрод рекламного трафика»\n")
    run_t.font.name = "Arial"
    run_t.font.size = Pt(20)
    run_t.font.bold = True
    run_t.font.color.rgb = RGBColor(31, 78, 120)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_s = sub.add_run("Архитектура, потоковая обработка (Kafka), ML-скоринг (XGBoost) и микросервисная реализация\n")
    run_s.font.size = Pt(12)
    run_s.font.italic = True
    run_s.font.color.rgb = RGBColor(89, 89, 89)

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_i = info.add_run("Студент: Денис Куравин\nТехнологии: Python 3.12, FastAPI, Kafka, XGBoost, Redis, ClickHouse, Docker\n")
    run_i.font.size = Pt(10)
    run_i.font.bold = True

    doc.add_paragraph("—" * 60)

    # Раздел 1
    h1 = doc.add_heading("1. Постановка задачи", level=1)
    doc.add_paragraph(
        "1.1. Проблема: В рекламных сетях (PPC/AdTech) до 20-30% трафика может составлять фрод (накрутка кликов ботами, "
        "headless-браузерами, фермами кликов). Это приводит к необоснованному расходу рекламных бюджетов клиентов.\n"
        "1.2. Цель: Создание высокопроизводительного сервиса потокового скоринга кликстрима с ультранизкой задержкой (< 15 мс) "
        "для мгновенного выявления и фильтрации нелегитимных кликов.\n"
        "1.3. Пользователи: Рекламный сервер (DSP/Ad Engine), аналитики данных и администраторы рекламной сети.\n"
        "1.4. Входные данные: ClickEvent (UUID клика, ID паблишера, IP, User-Agent, интервал задержки, устройство, ОС, гео).\n"
        "1.5. Выходные данные: FraudEvaluationResult (статус ALLOWED/SUSPICIOUS/BLOCKED, вероятность фрода, сработавшие правила, время ответа)."
    )

    # Раздел 2
    doc.add_heading("2. Архитектура системы", level=1)
    doc.add_paragraph(
        "Архитектура построена на принципах разделения Hot Path (быстрый синхронный скоринг через FastAPI + Redis) "
        "и Cold Path (потоковая аналитика в Kafka + батчевая вставка в ClickHouse для визуализации в Grafana).\n"
        "Сервисы:\n"
        "• Antifraud API Service (FastAPI) — синхронная оценка кликов с использованием цепочки обязанностей и гибридной стратегии скоринга;\n"
        "• Redis 7.2 — кэширование счетчиков частоты кликов со скользящими окнами (1 мин, 5 мин) и черные списки IP;\n"
        "• Apache Kafka — стриминг событий в топики clicks.raw, clicks.fraud, clicks.dlq;\n"
        "• ClickHouse — колоночная аналитическая база данных для долговременного хранения истории и построения отчетов;\n"
        "• Grafana — аналитический дашборд оперативного мониторинга ключевых показателей (Fraud Rate, RPS, Latency)."
    )

    # Раздел 3
    doc.add_heading("3. Стриминг и очереди сообщений (Apache Kafka)", level=1)
    doc.add_paragraph("Спецификация топиков:")
    
    table_k = doc.add_table(rows=1, cols=4)
    table_k.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table_k.rows[0].cells
    hdr[0].text = "Топик"
    hdr[1].text = "Partitions"
    hdr[2].text = "Формат"
    hdr[3].text = "Назначение"
    for c in hdr:
        set_cell_background(c, "D9E1F2")
        c.paragraphs[0].runs[0].font.bold = True

    k_data = [
        ("clicks.raw", "12", "JSON", "Сырой поток входящих кликов со всех точек приема"),
        ("clicks.fraud", "6", "JSON", "Выявленные мошеннические события для биллинга"),
        ("clicks.dlq", "3", "JSON + Error", "Dead Letter Queue для ошибочных сообщений")
    ]
    for row in k_data:
        r = table_k.add_row().cells
        for i, val in enumerate(row):
            r[i].text = val

    doc.add_paragraph("\nConsumer Groups: ad-fraud-detector-workers (12 воркеров), ad-clickhouse-analytics-sink (пачечная запись).")

    # Раздел 4
    doc.add_heading("4. Хранилища данных", level=1)
    doc.add_paragraph(
        "• Redis: выбран благодаря O(1) задержкам (< 0.5 мс) для проверки частоты запросов и черных списков.\n"
        "• ClickHouse: колоночная СУБД с компрессией ZSTD и движком MergeTree, партиционирование по месяцам toYYYYMM(event_time), "
        "сортировка по (publisher_id, campaign_id, event_time). Оптимальна для векторной аналитики миллиардов событий."
    )

    # Раздел 5
    doc.add_heading("5. API сервиса", level=1)
    doc.add_paragraph(
        "Реализованы эндпоинты:\n"
        "• POST /api/v1/clicks/evaluate — синхронная оценка одиночного клика;\n"
        "• POST /api/v1/clicks/batch — пакетная обработка кликов (чтение батчами из брокера);\n"
        "• GET /api/v1/metrics — аналитическая сводка (процент фрода, средняя задержка, топ IP);\n"
        "• POST /api/v1/strategy — динамическое переключение стратегии скоринга (hybrid, ml_only, rules_only);\n"
        "• GET /api/v1/health — проверка статуса сервиса и Circuit Breaker."
    )

    # Раздел 6
    doc.add_heading("6. Примененные паттерны проектирования", level=1)
    doc.add_paragraph(
        "1. Chain of Responsibility (Цепочка обязанностей): Организует последовательную фильтрацию "
        "(BlacklistIpHandler -> UserAgentBotHandler -> FastClickRateLimitHandler -> ScoringStrategyHandler). "
        "Позволяет отсекать явных ботов на ранних шагах без вызова тяжелого ML-инференса.\n\n"
        "2. Strategy (Стратегия): Семейство алгоритмов скоринга (RuleBasedStrategy, MLOnlyStrategy, HybridScoringStrategy). "
        "Позволяет динамически настраивать баланс эвристик и ML-модели.\n\n"
        "3. Repository (Репозиторий): Изолирует бизнес-логику от уровня хранения (IClickRepository, InMemoryClickRepository, "
        "ClickHouseRedisRepository). Обеспечивает автономность и локальное тестирование.\n\n"
        "4. Circuit Breaker (Предохранитель): Защищает сервис от каскадных сбоев при падении внешних баз и брокеров (CLOSED/OPEN/HALF_OPEN)."
    )

    # Раздел 7
    doc.add_heading("7. Модуль машинного обучения (XGBoost)", level=1)
    doc.add_paragraph(
        "Обучена модель градиентного бустинга XGBoost на синтетическом датасете кликстрима (20 000 записей). "
        "Конвейер признаков (FeaturePipeline) извлекает 9 параметров: частота кликов за 1 и 5 минут, интервал от показа до клика, "
        "сигнатура User-Agent, признак датацентрового IP, несовпадение устройства и ОС, ночной час."
    )

    table_m = doc.add_table(rows=1, cols=4)
    table_m.alignment = WD_TABLE_ALIGNMENT.CENTER
    m_hdr = table_m.rows[0].cells
    m_hdr[0].text = "Метрика"
    m_hdr[1].text = "Baseline (Logistic Regression)"
    m_hdr[2].text = "XGBoost Classifier"
    m_hdr[3].text = "Прирост"
    for c in m_hdr:
        set_cell_background(c, "E2EFDA")
        c.paragraphs[0].runs[0].font.bold = True

    m_data = [
        ("ROC-AUC", "0.9590", "0.9877", "+0.0287"),
        ("PR-AUC", "0.9098", "0.9559", "+0.0461"),
        ("F1-Score", "0.8485", "0.8809", "+0.0324"),
        ("Precision", "0.9657", "0.8869", "-"),
        ("Recall", "0.7567", "0.8750", "+11.83%")
    ]
    for row in m_data:
        r = table_m.add_row().cells
        for i, val in enumerate(row):
            r[i].text = val

    doc.add_paragraph(
        "\nТоп-3 важных признака: clicks_5min (45.3%), is_datacenter_ip (21.4%), clicks_1min (11.9%)."
    )

    # Разделы 8-10 (N/A)
    doc.add_heading("8. Разделы RL / LLM-RAG / Video-CV (Обоснование N/A)", level=1)
    doc.add_paragraph(
        "В соответствии со спецификацией Проекта №1 («Антифрод рекламного трафика»):\n"
        "• RL (Обучение с подкреплением): Не применимо, задача решена методом бинарной потоковой классификации с учителем.\n"
        "• LLM / RAG: Не применимо, анализ кликстрима требует жесткого лимита времени ответа < 15 мс и работает с табличными признаками.\n"
        "• Video / CV: Не применимо к Проекту №1 (компьютерное зрение предусмотрено в Проекте №2)."
    )

    # Разделы 11-13
    doc.add_heading("9. Надежность и Docker-развертывание", level=1)
    doc.add_paragraph(
        "• Идемпотентность по click_id.\n"
        "• Предохранитель Circuit Breaker для отказоустойчивости.\n"
        "• Dockerfile и docker-compose.yml для оркестрации API, Kafka, Zookeeper, Redis, ClickHouse, Grafana."
    )

    doc.add_heading("10. Тестирование и демонстрация", level=1)
    doc.add_paragraph(
        "Успешно выполнен сьют автоматических тестов (pytest): 7 из 7 тестов пройдены успешно (100%).\n"
        "Результаты симуляции реального потока кликов:\n"
        "• Всего обработано кликов: 30\n"
        "• Выявлено фрода: 7 (23.3%)\n"
        "• Средняя задержка обработки (Latency): 2.82 мс (норматив < 15 мс выполнен с пятикратным запасом)."
    )

    doc.add_heading("11. Выводы", level=1)
    doc.add_paragraph(
        "1. Создана полнофункциональная архитектура сервиса антифрода рекламного трафика.\n"
        "2. Реализовано сочетание правил и ML-модели XGBoost с высоким качеством (ROC-AUC 0.9877).\n"
        "3. Внедрены и протестированы паттерны Chain of Responsibility, Strategy, Repository, Circuit Breaker.\n"
        "4. Подготовлены все конфигурации развертывания и документация."
    )

    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(current_dir, "REPORT_PROJECT_1.docx")
    doc.save(out_path)
    print("Report generated successfully at:", out_path)

if __name__ == "__main__":
    generate_report()
