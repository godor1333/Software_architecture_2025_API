import time
from ..models import RAGQueryRequest
from ..patterns.facade import RAGSystemFacade

def run_demo():
    print("=" * 72)
    print("  ДЕМОНСТРАЦИЯ: RAG-ПОИСК И Q&A ПО УЧЕБНЫМ МАТЕРИАЛАМ")
    print("=" * 72)

    facade = RAGSystemFacade()

    # 1. Загрузка книги №1: Алгоритмы и структуры данных
    book_algo_content = (
        "Глава 7. Быстрая сортировка (QuickSort). "
        "Быстрая сортировка использует парадигму разделяй и властвуй. "
        "В среднем алгоритм выполняется за время O(n log n), однако в наихудшем случае, "
        "когда опорный элемент (pivot) выбирается неудачно (например, наименьший или наибольший элемент), "
        "время работы может деградировать до квадратичного O(n^2). "
        "Сортировка слиянием (MergeSort), в отличие от быстрой сортировки, гарантирует время работы O(n log n) "
        "даже в наихудшем случае, однако требует дополнительной памяти O(n) для объединения подмассивов. "
        "Быстрая сортировка работает на месте (in-place) с пространственной сложностью O(log n) для стека рекурсии, "
        "что делает её предпочтительной на практике для многих сценариев в оперативной памяти."
    )

    # 2. Загрузка книги №2: Проектирование распределенных систем
    book_dist_content = (
        "Глава 3. Надежность, масштабируемость и теорема CAP. "
        "Теорема CAP, сформулированная Эриком Брюером, утверждает, что в распределенной системе "
        "невозможно одновременно обеспечить все три свойства: Согласованность (Consistency), "
        "Доступность (Availability) и Устойчивость к разделению сети (Partition Tolerance). "
        "Поскольку сетевые сбои и разделения неизбежны в реальных распределенных сетях, разработчик обязан "
        "выбирать между согласованностью (CP-системы, например Apache HBase, ZooKeeper) и "
        "высокой доступностью (AP-системы, например Apache Cassandra, Amazon DynamoDB), "
        "жертвуя строгой мгновенной согласованностью в пользу итоговой согласованности (Eventual Consistency)."
    )

    print("\n[1] Индексация учебных материалов...")
    res1 = facade.index_book(
        title="Алгоритмы: построение и анализ (4-е изд.)",
        author="Томас Кормен, Чарльз Лейзерсон",
        content=book_algo_content,
        subject="Computer Science",
        total_pages=1320
    )
    print(f"  -> «{res1.title}»: создано {res1.chunks_indexed} чанков ({res1.processing_time_ms:.2f} ms)")

    res2 = facade.index_book(
        title="Высоконагруженные приложения: программирование, развитие, поддержка",
        author="Мартин Клеппман",
        content=book_dist_content,
        subject="Distributed Systems",
        total_pages=640
    )
    print(f"  -> «{res2.title}»: создано {res2.chunks_indexed} чанков ({res2.processing_time_ms:.2f} ms)")

    # 3. Выполнение студенческих запросов
    questions = [
        "В чем разница во времени работы и памяти между QuickSort и MergeSort в худшем случае?",
        "Что гласит теорема CAP и чем отличаются CP и AP системы?"
    ]

    for q_idx, q_text in enumerate(questions, 1):
        print("\n" + "-" * 72)
        print(f"  ВОПРОС {q_idx}: «{q_text}»")
        print("-" * 72)

        req = RAGQueryRequest(query=q_text, top_k=2, strategy="hybrid_keyword_vector")
        ans = facade.ask(req)

        print(f"Стратегия поиска:      {ans.search_strategy}")
        print(f"Время ответа (Latency): {ans.latency_ms:.2f} ms")
        print(f"Использовано чанков:   {ans.used_chunks_count}")
        print(f"\n{ans.generated_answer}")

        print("\nЦитируемые источники и релевантность:")
        for s_idx, src in enumerate(ans.sources, 1):
            print(f"  [{s_idx}] {src.author} — «{src.book_title}» (стр. {src.page_number}) | Сходство: {src.similarity_score:.1%}")

    print("\n" + "=" * 72)
    metrics = facade.get_metrics()
    print("  Итоговая сводка RAG-системы")
    print("=" * 72)
    print(f"Всего проиндексировано книг:    {metrics.total_books}")
    print(f"Всего векторных чанков:        {metrics.total_chunks}")
    print(f"Всего обслужено RAG-запросов:  {metrics.total_queries}")
    print(f"Средняя задержка поиска:       {metrics.avg_query_latency_ms:.2f} ms")
    print(f"Средний score релевантности:   {metrics.avg_retrieval_score:.1%}")
    print("=" * 72)

if __name__ == "__main__":
    run_demo()
