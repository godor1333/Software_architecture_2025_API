from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from ..models import BookDocument, RAGSystemMetrics

class IBookRepository(ABC):
    """Интерфейс репозитория книг и учебных материалов (Repository Pattern)."""

    @abstractmethod
    def save_book(self, book: BookDocument) -> None:
        pass

    @abstractmethod
    def get_by_id(self, book_id: str) -> Optional[BookDocument]:
        pass

    @abstractmethod
    def list_books(self, limit: int = 50) -> List[BookDocument]:
        pass

    @abstractmethod
    def record_query(self, latency_ms: float, avg_score: float) -> None:
        pass

    @abstractmethod
    def get_metrics(self, total_chunks: int = 0) -> RAGSystemMetrics:
        pass

class InMemoryBookRepository(IBookRepository):
    """Потокобезопасный In-Memory репозиторий для автономной работы и тестирования."""

    def __init__(self):
        self._books: Dict[str, BookDocument] = {}
        self._total_queries: int = 0
        self._total_latency_ms: float = 0.0
        self._total_scores: float = 0.0

    def save_book(self, book: BookDocument) -> None:
        self._books[book.book_id] = book

    def get_by_id(self, book_id: str) -> Optional[BookDocument]:
        return self._books.get(book_id)

    def list_books(self, limit: int = 50) -> List[BookDocument]:
        return list(self._books.values())[-limit:]

    def record_query(self, latency_ms: float, avg_score: float) -> None:
        self._total_queries += 1
        self._total_latency_ms += latency_ms
        self._total_scores += avg_score

    def get_metrics(self, total_chunks: int = 0) -> RAGSystemMetrics:
        avg_lat = (self._total_latency_ms / self._total_queries) if self._total_queries > 0 else 0.0
        avg_sc = (self._total_scores / self._total_queries) if self._total_queries > 0 else 0.0

        subjects = set(b.subject for b in self._books.values())

        return RAGSystemMetrics(
            total_books=len(self._books),
            total_chunks=total_chunks,
            total_queries=self._total_queries,
            avg_query_latency_ms=round(avg_lat, 2),
            avg_retrieval_score=round(avg_sc, 4),
            top_queried_subjects=list(subjects)[:5]
        )
