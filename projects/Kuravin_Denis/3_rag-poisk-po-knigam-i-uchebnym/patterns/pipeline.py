import time
from typing import List
from ..models import BookDocument, DocumentChunk, IndexingResponse
from ..rag.chunker import TextChunker
from ..rag.embeddings import EmbeddingEngine
from .adapter import IVectorDbAdapter
from .repository import IBookRepository

class IndexingContext:
    """Контекст конвейера индексации книги (Pipeline Pattern)."""

    def __init__(self, book: BookDocument):
        self.book = book
        self.chunks: List[DocumentChunk] = []
        self.indexed_count: int = 0
        self.start_time: float = time.time()
        self.response: Optional[IndexingResponse] = None

class BookIndexingPipeline:
    """Конвейер обработки и векторной индексации книги."""

    def __init__(
        self,
        chunker: TextChunker,
        embedding_engine: EmbeddingEngine,
        vector_adapter: IVectorDbAdapter,
        book_repository: IBookRepository
    ):
        self.chunker = chunker
        self.embedding_engine = embedding_engine
        self.vector_adapter = vector_adapter
        self.book_repository = book_repository

    def stage_1_validation(self, ctx: IndexingContext) -> None:
        if not ctx.book.content.strip():
            raise ValueError("Содержимое книги не может быть пустым.")
        if not ctx.book.title.strip():
            raise ValueError("Заголовок книги не может быть пустым.")

    def stage_2_chunking(self, ctx: IndexingContext) -> None:
        ctx.chunks = self.chunker.chunk_document(ctx.book)

    def stage_3_embeddings(self, ctx: IndexingContext) -> None:
        for ch in ctx.chunks:
            ch.embedding = self.embedding_engine.embed_text(ch.text)

    def stage_4_vector_indexing(self, ctx: IndexingContext) -> None:
        ctx.indexed_count = self.vector_adapter.upsert_chunks(ctx.chunks)

    def stage_5_persistence(self, ctx: IndexingContext) -> None:
        self.book_repository.save_book(ctx.book)
        elapsed_ms = (time.time() - ctx.start_time) * 1000.0
        ctx.response = IndexingResponse(
            book_id=ctx.book.book_id,
            title=ctx.book.title,
            chunks_indexed=ctx.indexed_count,
            processing_time_ms=round(elapsed_ms, 2),
            status="SUCCESS"
        )

    def execute(self, book: BookDocument) -> IndexingResponse:
        ctx = IndexingContext(book)
        self.stage_1_validation(ctx)
        self.stage_2_chunking(ctx)
        self.stage_3_embeddings(ctx)
        self.stage_4_vector_indexing(ctx)
        self.stage_5_persistence(ctx)
        return ctx.response
