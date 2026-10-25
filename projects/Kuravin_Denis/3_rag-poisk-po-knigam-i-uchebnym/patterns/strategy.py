from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import SourceCitation
from ..rag.vector_index import VectorIndex

class ISearchStrategy(ABC):
    """Интерфейс стратегии извлечения релевантных контекстов (Strategy Pattern)."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def retrieve(self, query: str, index: VectorIndex, top_k: int = 3, threshold: float = 0.20) -> List[SourceCitation]:
        pass

class DenseVectorSearchStrategy(ISearchStrategy):
    """Стратегия плотного семантического векторного поиска (HNSW Cosine)."""

    @property
    def name(self) -> str:
        return "dense_vector"

    def retrieve(self, query: str, index: VectorIndex, top_k: int = 3, threshold: float = 0.20) -> List[SourceCitation]:
        return index.search(query, top_k=top_k, threshold=threshold)

class HybridKeywordVectorStrategy(ISearchStrategy):
    """Гибридная стратегия (Векторный поиск + лексическое пересечение терминов BM25-like)."""

    @property
    def name(self) -> str:
        return "hybrid_keyword_vector"

    def retrieve(self, query: str, index: VectorIndex, top_k: int = 3, threshold: float = 0.15) -> List[SourceCitation]:
        base_results = index.search(query, top_k=top_k * 2, threshold=threshold)
        query_words = set(query.lower().split())

        re_scored = []
        for cite in base_results:
            chunk_words = set(cite.chunk_text.lower().split())
            intersection = len(query_words.intersection(chunk_words))
            keyword_bonus = min(0.3, intersection * 0.05)

            # Взвешенный комбинированный скор: 0.75 Vector + 0.25 Keyword
            combined_score = min(1.0, (cite.similarity_score * 0.75) + keyword_bonus)

            re_scored.append(SourceCitation(
                book_title=cite.book_title,
                author=cite.author,
                page_number=cite.page_number,
                similarity_score=round(combined_score, 4),
                chunk_text=cite.chunk_text
            ))

        re_scored.sort(key=lambda x: x.similarity_score, reverse=True)
        return re_scored[:top_k]
