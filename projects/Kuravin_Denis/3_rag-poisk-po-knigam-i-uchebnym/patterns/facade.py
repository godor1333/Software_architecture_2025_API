import time
from typing import List, Optional
from ..models import (
    BookDocument,
    DocumentChunk,
    RAGQueryRequest,
    RAGQueryResponse,
    IndexingResponse,
    RAGSystemMetrics
)
from ..rag.chunker import TextChunker
from ..rag.embeddings import EmbeddingEngine
from ..rag.vector_index import VectorIndex
from .strategy import ISearchStrategy, DenseVectorSearchStrategy, HybridKeywordVectorStrategy
from .adapter import IVectorDbAdapter, LocalVectorDbAdapter, ILLMAdapter, LocalGroundedLLMAdapter
from .repository import IBookRepository, InMemoryBookRepository
from .pipeline import BookIndexingPipeline

class RAGSystemFacade:
    """Паттерн Фасад (Facade Pattern) — единая точка входа для индексации и вопросно-ответной системы."""

    def __init__(
        self,
        vector_adapter: Optional[IVectorDbAdapter] = None,
        llm_adapter: Optional[ILLMAdapter] = None,
        book_repository: Optional[IBookRepository] = None
    ):
        self.chunker = TextChunker()
        self.embedding_engine = EmbeddingEngine()
        self.vector_index = VectorIndex(self.embedding_engine)

        self.vector_adapter = vector_adapter or LocalVectorDbAdapter(self.vector_index)
        self.llm_adapter = llm_adapter or LocalGroundedLLMAdapter()
        self.book_repository = book_repository or InMemoryBookRepository()

        self.pipeline = BookIndexingPipeline(
            chunker=self.chunker,
            embedding_engine=self.embedding_engine,
            vector_adapter=self.vector_adapter,
            book_repository=self.book_repository
        )

        self.strategies = {
            "dense_vector": DenseVectorSearchStrategy(),
            "hybrid_keyword_vector": HybridKeywordVectorStrategy()
        }

    def index_book(
        self,
        title: str,
        author: str,
        content: str,
        subject: str = "Computer Science",
        total_pages: int = 1
    ) -> IndexingResponse:
        """Индексирует книгу через внутренний Pipeline."""
        doc = BookDocument(
            title=title,
            author=author,
            subject=subject,
            total_pages=total_pages,
            content=content
        )
        return self.pipeline.execute(doc)

    def ask(self, request: RAGQueryRequest) -> RAGQueryResponse:
        """Выполняет RAG-поиск релевантных контекстов и генерирует обоснованный ответ."""
        start_time = time.time()

        strategy = self.strategies.get(request.strategy, self.strategies["dense_vector"])
        citations = strategy.retrieve(
            query=request.query,
            index=self.vector_index,
            top_k=request.top_k
        )

        # Генерация ответа через LLM-адаптер
        answer = self.llm_adapter.generate_grounded_answer(request.query, citations)

        elapsed_ms = (time.time() - start_time) * 1000.0
        avg_score = (sum(c.similarity_score for c in citations) / len(citations)) if citations else 0.0

        # Фиксируем запрос в репозитории
        self.book_repository.record_query(latency_ms=elapsed_ms, avg_score=avg_score)

        return RAGQueryResponse(
            query=request.query,
            generated_answer=answer,
            sources=citations,
            used_chunks_count=len(citations),
            search_strategy=strategy.name,
            latency_ms=round(elapsed_ms, 2)
        )

    def get_metrics(self) -> RAGSystemMetrics:
        return self.book_repository.get_metrics(total_chunks=self.vector_index.total_vectors)

    def list_books(self, limit: int = 50) -> List[BookDocument]:
        return self.book_repository.list_books(limit=limit)
