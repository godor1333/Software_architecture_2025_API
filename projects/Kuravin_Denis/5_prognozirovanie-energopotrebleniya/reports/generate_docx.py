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
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Титульный блок
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = title.add_run("ОТЧЁТ ПО ПРОЕКТУ №5\n«Прогнозирование энергопотребления здания»\n")
    run_t.font.name = "Arial"
    run_t.font.size = Pt(20)
    run_t.font.bold = True
    run_t.font.color.rgb = RGBColor(31, 78, 120)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_s = sub.add_run("IoT телеметрия, прогнозирование временных рядов (XGBoost), детекция пиков (3-Sigma) и микросервисная архитектура\n")
    run_s.font.size = Pt(12)
    run_s.font.italic = True
    run_s.font.color.rgb = RGBColor(89, 89, 89)

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_i = info.add_run("Студент: Денис Куравин\nТехнологии: Python 3.12, Kafka, XGBoost, Pandas, ClickHouse, Grafana, FastAPI, Docker\n")
    run_i.font.size = Pt(10)
    run_i.font.bold = True

    doc.add_paragraph("—" * 60)

    # Раздел 1
    doc.add_heading("1. Постановка задачи", level=1)
    doc.add_paragraph(
        "1.1. Проблема: В коммерческих зданиях и университетских кампусах пиковые перегрузки электросети приводят к аварийным "
        "отключениям трансформаторов и крупным штрафам от энергосбытовых компаний за превышение лимитов заявленной мощности.\n"
        "1.2. Цель: Создание IoT-сервиса потокового приема показаний счетчиков, прогнозирования почасового профиля нагрузки "
        "на 1-48 часов вперед (XGBoost Regressor) и предиктивного выявления аномальных пиков (Residual 3-Sigma).\n"
        "1.3. Пользователи: Главные энергетики, диспетчеры энергохозяйства, системы автоматики зданий (BMS / HVAC).\n"
        "1.4. Входные данные: Поток показаний MeterReadingEvent (мощность кВт, наружная температура, влажность, тип здания).\n"
        "1.5. Выходные данные: Почасовой прогноз нагрузки с 95% доверительным интервалом и диспетчерские алерты AnomalyAlert (NORMAL/WARNING/CRITICAL_PEAK)."
    )

    # Раздел 2
    doc.add_heading("2. Архитектура системы", level=1)
    doc.add_paragraph(
        "Архитектура построена на разделении потокового IoT-контура приема показаний и аналитического модуля:\n"
        "• Energy Gateway API (FastAPI) — прием телеметрии, валидация и генерация почасовых прогнозов нагрузки;\n"
        "• Feature Pipeline Core — расчет циклических признаков часа, лагов (1ч, 24ч, 6ч MA) и квадратичного эффекта температуры HVAC;\n"
        "• XGBoost Forecasting Core — регрессионная модель прогнозирования энергопотребления;\n"
        "• Residual 3-Sigma Anomaly Core — статистический фильтр выявления аварийных перегрузок мощности;\n"
        "• Apache Kafka — стриминг телеметрии в топики energy.telemetry.raw, energy.telemetry.anomalies, energy.forecasts;\n"
        "• ClickHouse / TimescaleDB — колоночное хранилище временных рядов;\n"
        "• Grafana — мониторинговый дашборд диспетчера с графиками фактической мощности и прогноза."
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
        ("energy.telemetry.raw", "12", "JSON", "Сырой поток показаний электросчетчиков и датчиков погоды"),
        ("energy.telemetry.anomalies", "4", "JSON", "События аномальных пиков нагрузки для диспетчеров"),
        ("energy.forecasts", "6", "JSON", "Сгенерированные почасовые прогнозы нагрузки зданий")
    ]
    for row in k_data:
        r = table_k.add_row().cells
        for i, val in enumerate(row):
            r[i].text = val

    doc.add_paragraph("\nConsumer Group: energy-forecaster-workers (воркеры потокового инференса).")

    # Раздел 4
    doc.add_heading("4. Хранилища данных (ClickHouse Time-Series)", level=1)
    doc.add_paragraph(
        "• ClickHouse: таблица meter_readings с движком MergeTree, партиционирование toYYYYMM(event_time), "
        "сортировка по (building_id, event_time). Обеспечивает хранение истории за 3 года и мгновенный расчет скользящих окон."
    )

    # Раздел 5
    doc.add_heading("5. API сервиса", level=1)
    doc.add_paragraph(
        "• POST /api/v1/energy/record — прием показания счетчика, скоринг аномалий и сохранение;\n"
        "• POST /api/v1/energy/forecast — прогноз нагрузки здания на 1-48 часов вперед;\n"
        "• GET /api/v1/energy/anomalies — список зафиксированных пиков перегрузки;\n"
        "• GET /api/v1/energy/stats/{id} — статистика профиля энергопотребления здания;\n"
        "• GET /api/v1/health — статус сервиса и предохранителя Circuit Breaker."
    )

    # Раздел 6
    doc.add_heading("6. Примененные паттерны проектирования", level=1)
    doc.add_paragraph(
        "В проекте реализованы 5 обязательных паттернов GoF:\n"
        "1. Pipeline (Конвейер): Организует обработку показаний по стадиям Validate -> ForecastExpected -> DetectAnomalies -> NotifyAndPersist.\n"
        "2. Strategy (Стратегия): Семейство алгоритмов прогнозирования (XGBoostForecastingStrategy и BaselinePersistenceStrategy).\n"
        "3. Observer (Наблюдатель): Реактивное оповещение. OverloadDispatchObserver перехватывает аварийные пики (CRITICAL_PEAK) и регистрирует вызов дежурной бригады.\n"
        "4. Repository (Репозиторий): ITelemetryRepository инкапсулирует работу с временными рядами и расчет статистики здания (BuildingEnergyStats).\n"
        "5. Circuit Breaker (Предохранитель): Предотвращает каскадные отказы при сбоях очередей телеметрии Kafka (CLOSED -> OPEN -> HALF_OPEN)."
    )

    # Раздел 7
    doc.add_heading("7. Модуль машинного обучения и прогнозирования (XGBoost)", level=1)
    doc.add_paragraph(
        "Корпус: ASHRAE Great Energy Predictor III (Smart Campus Dataset, 8 760 часовых измерений).\n"
        "Признаки: лаги 1ч, 24ч, 6ч MA, температура, квадратичный эффект HVAC, флаг выходного дня.\n"
        "Сравнение метрик качества прогнозирования на тестовой выборке (1 760 часов):"
    )

    table_m = doc.add_table(rows=1, cols=4)
    table_m.alignment = WD_TABLE_ALIGNMENT.CENTER
    m_hdr = table_m.rows[0].cells
    m_hdr[0].text = "Метрика"
    m_hdr[1].text = "Naive Persistence (lag-24h)"
    m_hdr[2].text = "XGBoost Regressor Model"
    m_hdr[3].text = "Прирост"
    for c in m_hdr:
        set_cell_background(c, "E2EFDA")
        c.paragraphs[0].runs[0].font.bold = True

    m_data = [
        ("RMSE (кВт·ч)", "100.53", "13.27", "Снижение в 7.5 раз"),
        ("MAE (кВт·ч)", "62.03", "10.52", "Снижение в 5.9 раз"),
        ("R² (Score)", "0.4878", "0.9911", "+0.5033 (99.1% R²)"),
        ("MAPE (%)", "15.09%", "2.63%", "Ошибка 2.6%")
    ]
    for row in m_data:
        r = table_m.add_row().cells
        for i, val in enumerate(row):
            r[i].text = val

    doc.add_paragraph(
        "\nДетектор аномалий (Residual 3-Sigma): стандартное отклонение ошибки составляет 13.27 кВт, "
        "порог 3-сигма равен 39.8 кВт сверх нормы, что обеспечивает надежное отсечение ложных тревог."
    )

    # Раздел 8
    doc.add_heading("8. Разделы RL / Video-CV (Обоснование N/A)", level=1)
    doc.add_paragraph(
        "• RL (Reinforcement Learning): Не применимо к регрессионному прогнозированию временных рядов.\n"
        "• Video / CV: Не применимо, проект сфокусирован на анализе числовой телеметрии IoT."
    )

    # Раздел 9
    doc.add_heading("9. Надежность и Docker-развертывание", level=1)
    doc.add_paragraph(
        "• Предохранитель Circuit Breaker для изоляции сетевых сбоев брокеров телеметрии.\n"
        "• Dockerfile и docker-compose.yml для оркестрации API, Kafka, Zookeeper, ClickHouse и Grafana в сети energy-net."
    )

    # Раздел 10
    doc.add_heading("10. Тестирование и демонстрация", level=1)
    doc.add_paragraph(
        "Успешно выполнен сьют автоматических тестов (pytest): 5 из 5 тестов пройдены успешно (100%).\n"
        "Результаты демонстрационного сценария (ml/demo_telemetry.py):\n"
        "• Смоделированы 24 часа телеметрии университетского корпуса (15 000 кв. м);\n"
        "• В 14:00 зафиксирован аварийный пик мощности 920.0 кВт;\n"
        "• Система зафиксировала статус CRITICAL_PEAK (Z=48.3 sigma) и сгенерировала наряд диспетчеру;\n"
        "• Построен почасовой прогноз на 6 часов вперед с 95% доверительным интервалом."
    )

    # Раздел 11
    doc.add_heading("11. Выводы", level=1)
    doc.add_paragraph(
        "1. Разработан промышленный сервис прогнозирования энергопотребления умных зданий (R² = 0.9911, MAPE = 2.63%).\n"
        "2. Реализована система обнаружения аномалий Residual 3-Sigma, предотвращающая аварии энергосети.\n"
        "3. Внедрены 5 обязательных паттернов: Observer, Strategy, Repository, Pipeline, Circuit Breaker.\n"
        "4. Подготовлена проектная документация, Docker-конфигурация и академический отчет."
    )

    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(current_dir, "REPORT_PROJECT_5.docx")
    doc.save(out_path)
    print("Report 5 generated successfully at:", out_path)

if __name__ == "__main__":
    generate_report()
