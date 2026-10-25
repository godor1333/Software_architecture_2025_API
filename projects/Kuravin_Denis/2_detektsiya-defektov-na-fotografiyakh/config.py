import os
from pydantic import BaseModel

class Settings(BaseModel):
    app_name: str = "Car Damage Detection & Inspection Service"
    app_version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # API
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8001"))

    # MinIO / S3
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket_raw: str = "car-photos-raw"
    minio_bucket_annotated: str = "car-photos-annotated"
    minio_use_ssl: bool = False

    # PostgreSQL
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "cardamage")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")

    # CV / Inference
    image_input_size: int = 640
    confidence_threshold: float = 0.45
    iou_threshold: float = 0.50
    default_detector_strategy: str = "yolov8_fast"

    # Fallback
    use_inmemory_fallback: bool = True

settings = Settings()
