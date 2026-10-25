import re
from typing import List
from ..models import BookDocument, DocumentChunk

class TextChunker:
    """Модуль семантического разбиения текстов книг на чанки со скользящим окном."""

    def __init__(self, chunk_size_words: int = 120, overlap_words: int = 25):
        self.chunk_size = chunk_size_words
        self.overlap = overlap_words

    def split_into_sentences(self, text: str) -> List[str]:
        """Разбиение текста на предложения с сохранением пунктуации."""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def chunk_document(self, doc: BookDocument) -> List[DocumentChunk]:
        """Разбивает книгу на перекрывающиеся семантические фрагменты."""
        words = doc.content.split()
        if not words:
            return []

        chunks: List[DocumentChunk] = []
        step = max(1, self.chunk_size - self.overlap)
        chunk_idx = 0

        # Оценка страниц: примерно 250 слов на книжную страницу
        words_per_page = 250

        for start in range(0, len(words), step):
            end = min(len(words), start + self.chunk_size)
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            est_page = max(1, (start // words_per_page) + 1)

            chunks.append(DocumentChunk(
                book_id=doc.book_id,
                book_title=doc.title,
                author=doc.author,
                chunk_index=chunk_idx,
                page_number=est_page,
                text=chunk_text
            ))
            chunk_idx += 1

            if end >= len(words):
                break

        return chunks
