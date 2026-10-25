import time
from ..models import NewsItem
from ..api.main import pipeline, repository, risk_observer

NEWS_FEED = [
    {
        "title": "Сбербанк объявил рекордные дивиденды по итогам года",
        "content": "Наблюдательный совет Сбербанка рекомендовал выплатить рекордные дивиденды в размере 33.3 рубля на акцию благодаря сильному росту чистой прибыли по МСФО. Аналитики повысили целевой таргет по акциям SBER.",
        "source": "РБК Инвестиции"
    },
    {
        "title": "Газпром зафиксировал чистый убыток на фоне падения экспорта в Европу",
        "content": "ПАО Газпром отчиталось о чистом убытке за отчетный период из-за резкого снижения объемов прокачки и ухудшения прогнозов. Инвесторы опасаются отказа от выплаты дивидендов.",
        "source": "Интерфакс"
    },
    {
        "title": "Яндекс продемонстрировал рост выручки и существенное падение издержек",
        "content": "Технологический холдинг Яндекс (YDEX) опубликовал квартальный отчет: выручка сегмента Поиск и Портал выросла на 32%, при этом зафиксировано резкое падение издержек на инфраструктуру.",
        "source": "Ведомости"
    },
    {
        "title": "Совет директоров Лукойла утвердил программу байбэк",
        "content": "Нефтяная компания Лукойл запустила программу обратного выкупа акций (buyback) с рынка и рекомендовала увеличение дивидендов за 9 месяцев.",
        "source": "Коммерсантъ"
    },
    {
        "title": "Т-Банк отчитался о стабильном росте клиентской базы",
        "content": "Финансовая группа Т-Банк (ТКС Холдинг) подвела итоги месяца: число активных пользователей превысило 42 миллиона человек, кредитный портфель сохраняет устойчивость.",
        "source": "Прайм"
    },
    {
        "title": "Nvidia отчиталась о рекордных финансовых показателях и превысила прогнозы",
        "content": "Акции Nvidia (NVDA) взлетели на постмаркете на 8%: выручка от дата-центров превзошла консенсус-прогноз аналитиков (beat estimate) на фоне глобального спроса на ИИ-чипы.",
        "source": "Bloomberg"
    }
]

def run_streaming_demo():
    print("=" * 75)
    print("  ДЕМОНСТРАЦИЯ: ПОТОКОВЫЙ АНАЛИЗ ТОНАЛЬНОСТИ ФИНАНСОВЫХ НОВОСТЕЙ (NLP/NER)")
    print("=" * 75)

    for i, raw in enumerate(NEWS_FEED, 1):
        item = NewsItem(
            title=raw["title"],
            content=raw["content"],
            source=raw["source"]
        )

        res = pipeline.execute(item)
        tickers_str = ", ".join([f"{e.ticker} ({e.name})" for e in res.entities]) if res.entities else "НЕТ"
        sentiment_tag = f"[{res.overall_sentiment.value}]"

        print(f"\n[Новость {i:02d}] {sentiment_tag:<12} Score: {res.sentiment_score:+0.2f} | Conf: {res.confidence:.0%}")
        print(f"Заголовок:    {res.title}")
        print(f"Компании/NER: {tickers_str}")
        print(f"Драйверы:     {', '.join(res.key_drivers)}")
        print(f"Задержка:     {res.processing_time_ms:.2f} ms")
        time.sleep(0.01)

    print("\n" + "=" * 75)
    print("  ТЕПЛОВАЯ КАРТА РЫНКА (MARKET SENTIMENT OVERVIEW)")
    print("=" * 75)
    overview = repository.get_all_companies_sentiment()
    print(f"{'Тикер':<8} {'Компания':<24} {'Новостей':<10} {'Сентимент':<12} {'Тренд'}")
    print("-" * 75)
    for comp in overview:
        trend_str = f"[+] {comp.market_trend.value}" if comp.market_trend.value == "BULLISH" else (
            f"[-] {comp.market_trend.value}" if comp.market_trend.value == "BEARISH" else f"[=] {comp.market_trend.value}"
        )
        print(f"{comp.ticker:<8} {comp.company_name[:22]:<24} {comp.total_news_count:<10} {comp.sentiment_index:+0.3f}{' ':<6} {trend_str}")

    print("\n" + "=" * 75)
    print(f"Сработавших риск-алертов Observer: {len(risk_observer.triggered_alerts)}")
    for alt in risk_observer.triggered_alerts:
        print(f"  [!] ВНИМАНИЕ: {', '.join(alt['tickers'])} | Скор: {alt['sentiment_score']} | {alt['title']}")
    print("=" * 75)

if __name__ == "__main__":
    run_streaming_demo()
