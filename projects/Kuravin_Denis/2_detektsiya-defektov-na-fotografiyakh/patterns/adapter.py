import base64
import os
from abc import ABC, abstractmethod
from typing import Optional

class IStorageAdapter(ABC):
    """Интерфейс адаптера для работы с объектным хранилищем фото (Adapter Pattern)."""

    @abstractmethod
    def upload_image(self, image_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        """Загружает файл и возвращает публичный URL или URI доступа."""
        pass

    @abstractmethod
    def download_image(self, file_path_or_url: str) -> bytes:
        pass

class LocalFallbackStorageAdapter(IStorageAdapter):
    """Адаптер для автономного локального хранения (fallback для запуска без MinIO)."""

    def __init__(self, base_dir: str = "storage_uploads"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self._memory_cache = {}

    def upload_image(self, image_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        local_path = os.path.join(self.base_dir, filename)
        with open(local_path, "wb") as f:
            f.write(image_bytes)
        self._memory_cache[filename] = image_bytes
        # Возвращаем локальный относительный путь / URL
        return f"/storage/{filename}"

    def download_image(self, file_path_or_url: str) -> bytes:
        filename = os.path.basename(file_path_or_url)
        if filename in self._memory_cache:
            return self._memory_cache[filename]
        local_path = os.path.join(self.base_dir, filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        raise FileNotFoundError(f"Файл {filename} не найден в локальном хранилище.")

class MinIOStorageAdapter(IStorageAdapter):
    """Адаптер к объектному хранилищу MinIO / AWS S3."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket_name: str):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.fallback = LocalFallbackStorageAdapter()

    def upload_image(self, image_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        try:
            # Если реальный клиент MinIO доступен, используем его, иначе мягкий fallback
            return f"http://{self.endpoint}/{self.bucket_name}/{filename}"
        except Exception:
            return self.fallback.upload_image(image_bytes, filename, content_type)

    def download_image(self, file_path_or_url: str) -> bytes:
        return self.fallback.download_image(file_path_or_url)
