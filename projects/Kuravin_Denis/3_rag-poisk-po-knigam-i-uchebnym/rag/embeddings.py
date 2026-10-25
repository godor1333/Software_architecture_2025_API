import math
import hashlib
import numpy as np
from typing import List

class EmbeddingEngine:
    """Генератор плотных векторных представлений (Embeddings) размерности 384 с субсловными n-граммами и L2-нормализацией."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        """Генерирует семантический вектор 384D на основе токенов и символьных 3-5 грамм."""
        raw_tokens = text.lower().split()
        vector = np.zeros(self.dimension, dtype=np.float32)

        if not raw_tokens:
            return vector.tolist()

        for word in raw_tokens:
            clean = "".join(c for c in word if c.isalnum())
            if not clean:
                continue

            # Полное слово
            h = int(hashlib.md5(clean.encode("utf-8")).hexdigest(), 16)
            vector[h % self.dimension] += 2.0

            # Символьные n-граммы от 3 до 5 символов для устойчивости к морфологии
            if len(clean) >= 3:
                for n in range(3, min(6, len(clean) + 1)):
                    for i in range(len(clean) - n + 1):
                        sub = clean[i:i+n]
                        hs = int(hashlib.md5(sub.encode("utf-8")).hexdigest(), 16)
                        vector[hs % self.dimension] += 0.8

        # L2-нормализация
        norm = np.linalg.norm(vector)
        if norm > 1e-6:
            vector = vector / norm

        return vector.tolist()

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Расчет косинусного сходства между двумя векторами."""
        arr1 = np.array(v1, dtype=np.float32)
        arr2 = np.array(v2, dtype=np.float32)
        dot = float(np.dot(arr1, arr2))
        norm1 = float(np.linalg.norm(arr1))
        norm2 = float(np.linalg.norm(arr2))
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))
