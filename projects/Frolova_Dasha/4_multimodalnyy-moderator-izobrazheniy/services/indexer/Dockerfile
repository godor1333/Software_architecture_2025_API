FROM python:3.11-slim
WORKDIR /app
COPY requirements-svc.txt .
RUN pip install --no-cache-dir -r requirements-svc.txt
COPY common/ common/
COPY services/indexer/ services/indexer/
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "services.indexer.main"]
