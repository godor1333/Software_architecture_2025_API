FROM python:3.11-slim
WORKDIR /app
COPY requirements-svc.txt .
RUN pip install --no-cache-dir -r requirements-svc.txt
COPY common/ common/
COPY services/api/ services/api/
ENV PYTHONPATH=/app
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
