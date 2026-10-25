import os
from pydantic import BaseModel

class Settings(BaseModel):
    app_name: str = "Academic Books & Educational RAG System"
    app_version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # API
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8002"))

    # Qdrant Vector DB
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_collection: str = "textbooks_collection"
    embedding_dimension: int = 384

    # MinIO / S3
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = "books-storage"

    # Kafka
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic_ingest: str = "books.ingestion"
    kafka_topic_indexed: str = "books.indexed"
    kafka_consumer_group: str = "rag-indexer-group"

    # RAG Search & Chunking
    chunk_size_words: int = 150
    chunk_overlap_words: int = 30
    default_top_k: int = 3
    similarity_threshold: float = 0.55
    max_tokens_generate: int = 512

    # Fallback
    use_inmemory_fallback: bool = True

settings = Settings()
