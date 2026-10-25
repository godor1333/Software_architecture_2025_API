import pytest
from fastapi.testclient import TestClient
from project_3_rag_books.api.main import app
from project_3_rag_books.models import BookDocument, RAGQueryRequest
from project_3_rag_books.rag.chunker import TextChunker
from project_3_rag_books.rag.embeddings import EmbeddingEngine
from project_3_rag_books.rag.vector_index import VectorIndex
from project_3_rag_books.patterns.facade import RAGSystemFacade

client = TestClient(app)

def test_chunker_logic():
    chunker = TextChunker(chunk_size_words=20, overlap_words=5)
    text = " ".join([f"word_{i}" for i in range(50)])
    doc = BookDocument(title="Test", author="Author", content=text)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 3
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    # Проверка перекрытия
    w0 = set(chunks[0].text.split())
    w1 = set(chunks[1].text.split())
    assert len(w0.intersection(w1)) >= 4

def test_embeddings_engine():
    engine = EmbeddingEngine(dimension=384)
    v1 = engine.embed_text("Быстрая сортировка QuickSort")
    v2 = engine.embed_text("Алгоритм сортировки QuickSort массивов")
    v3 = engine.embed_text("Кулинарный рецепт яблочного пирога")

    assert len(v1) == 384
    sim_related = engine.cosine_similarity(v1, v2)
    sim_unrelated = engine.cosine_similarity(v1, v3)

    assert sim_related > sim_unrelated
    assert engine.cosine_similarity(v1, v1) >= 0.999

def test_vector_index_search():
    engine = EmbeddingEngine()
    index = VectorIndex(engine)
    chunker = TextChunker(chunk_size_words=30, overlap_words=5)

    doc = BookDocument(
        title="Операционные системы",
        author="Э. Таненбаум",
        content="Взаимная блокировка или deadlock возникает когда два или более процессов заблокированы в ожидании ресурсов."
    )
    chunks = chunker.chunk_document(doc)
    index.add_chunks(chunks)

    results = index.search("Что такое deadlock и блокировка процессов?", top_k=1)
    assert len(results) == 1
    assert "deadlock" in results[0].chunk_text.lower()
    assert results[0].book_title == "Операционные системы"

def test_rag_facade_end_to_end():
    facade = RAGSystemFacade()
    res = facade.index_book(
        title="Базы данных",
        author="К. Дж. Дейт",
        content="Реляционная модель данных предложена Эдгаром Коддом в 1970 году. В основе лежит понятие отношения или таблицы."
    )
    assert res.chunks_indexed >= 1

    req = RAGQueryRequest(query="Кто и когда предложил реляционную модель данных?", top_k=1)
    ans = facade.ask(req)

    assert len(ans.sources) >= 1
    assert "Эдгаром Коддом" in ans.generated_answer
    assert ans.sources[0].author == "К. Дж. Дейт"

def test_api_health_and_query():
    # 1. Health
    h_resp = client.get("/api/v1/health")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "healthy"

    # 2. Index
    idx_payload = {
        "title": "Учебник сетей",
        "author": "Олифер",
        "subject": "Networks",
        "total_pages": 400,
        "content": "Модель OSI состоит из семи уровней от физического до прикладного уровня."
    }
    i_resp = client.post("/api/v1/rag/index", json=idx_payload)
    assert i_resp.status_code == 200
    assert i_resp.json()["status"] == "SUCCESS"

    # 3. Query
    q_payload = {
        "query": "Сколько уровней в модели OSI?",
        "top_k": 2,
        "strategy": "dense_vector"
    }
    q_resp = client.post("/api/v1/rag/query", json=q_payload)
    assert q_resp.status_code == 200
    data = q_resp.json()
    assert len(data["sources"]) >= 1
    assert "семи уровней" in data["generated_answer"]

    # 4. Metrics
    m_resp = client.get("/api/v1/rag/metrics")
    assert m_resp.status_code == 200
    assert m_resp.json()["total_books"] >= 1
