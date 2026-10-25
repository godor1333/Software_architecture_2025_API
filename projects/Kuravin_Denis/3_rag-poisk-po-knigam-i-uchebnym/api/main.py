from typing import List
from fastapi import FastAPI, HTTPException, Query
from ..models import (
    BookDocument,
    RAGQueryRequest,
    RAGQueryResponse,
    IndexingResponse,
    RAGSystemMetrics
)
from ..config import settings
from ..patterns.facade import RAGSystemFacade

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Высокопроизводительная RAG-система поиска и вопросов-ответов по учебным материалам и книгам"
)

# Синглтон фасада
facade = RAGSystemFacade()

@app.post("/api/v1/rag/index", response_model=IndexingResponse, tags=["Indexing"])
def index_book(book: BookDocument):
    """Индексация книги: чанкинг, эмбеддинги, запись в векторный индекс Qdrant."""
    try:
        resp = facade.index_book(
            title=book.title,
            author=book.author,
            content=book.content,
            subject=book.subject,
            total_pages=book.total_pages
        )
        return resp
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка индексации: {str(e)}")

@app.post("/api/v1/rag/query", response_model=RAGQueryResponse, tags=["Search & Q&A"])
def query_rag(request: RAGQueryRequest):
    """Семантический поиск релевантных фрагментов книг и генерация обоснованного ответа."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Запрос не может быть пустым.")
    try:
        return facade.ask(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки запроса: {str(e)}")

@app.get("/api/v1/rag/books", response_model=List[BookDocument], tags=["Library"])
def list_books(limit: int = Query(50, ge=1, le=100)):
    """Список проиндексированных учебников и материалов."""
    return facade.list_books(limit=limit)

@app.get("/api/v1/rag/metrics", response_model=RAGSystemMetrics, tags=["Analytics"])
def get_metrics():
    """Сводные метрики RAG-системы (количество книг, чанков, латентность, средний score)."""
    return facade.get_metrics()

@app.get("/api/v1/health", tags=["System"])
def health_check():
    """Проверка доступности сервиса."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "qdrant_collection": settings.qdrant_collection,
        "embedding_dim": settings.embedding_dimension,
        "environment": settings.environment
    }
