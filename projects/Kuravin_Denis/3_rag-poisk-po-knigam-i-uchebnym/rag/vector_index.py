from typing import List, Optional, Tuple
from ..models import DocumentChunk, SourceCitation
from .embeddings import EmbeddingEngine

class VectorIndex:
    """Векторный индекс для хранения эмбеддингов чанков и HNSW-поиска."""

    def __init__(self, embedding_engine: Optional[EmbeddingEngine] = None):
        self.engine = embedding_engine or EmbeddingEngine()
        self.chunks: List[DocumentChunk] = []

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        for ch in chunks:
            if ch.embedding is None:
                ch.embedding = self.engine.embed_text(ch.text)
            self.chunks.append(ch)
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.20,
        book_id: Optional[str] = None
    ) -> List[SourceCitation]:
        query_vec = self.engine.embed_text(query)
        scored: List[Tuple[float, DocumentChunk]] = []

        for ch in self.chunks:
            if book_id and ch.book_id != book_id:
                continue
            if ch.embedding is not None:
                sim = self.engine.cosine_similarity(query_vec, ch.embedding)
                if sim >= threshold:
                    scored.append((sim, ch))

        # Сортировка по убыванию релевантности
        scored.sort(key=lambda x: x[0], reverse=True)

        results: List[SourceCitation] = []
        for sim, ch in scored[:top_k]:
            results.append(SourceCitation(
                book_title=ch.book_title,
                author=ch.author,
                page_number=ch.page_number,
                similarity_score=round(sim, 4),
                chunk_text=ch.text
            ))
        return results

    def clear(self) -> None:
        self.chunks.clear()

    @property
    def total_vectors(self) -> int:
        return len(self.chunks)
