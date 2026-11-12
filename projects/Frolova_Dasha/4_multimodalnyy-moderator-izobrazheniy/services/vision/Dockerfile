FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 && rm -rf /var/lib/apt/lists/*
COPY requirements-vision.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 300 torch==2.5.1 torchvision==0.20.1

RUN pip install --no-cache-dir --retries 10 --timeout 300 \
    transformers==4.47.1 Pillow==11.1.0 numpy==1.26.4 \
    aiokafka==0.12.0 kafka-python==2.0.2 boto3==1.35.90 imagehash==4.3.1
RUN pip install --no-cache-dir --retries 10 --timeout 300 confluent-kafka==2.5.0 minio==7.2.12
COPY common/ common/
COPY services/vision/ services/vision/
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "services.vision.main"]
