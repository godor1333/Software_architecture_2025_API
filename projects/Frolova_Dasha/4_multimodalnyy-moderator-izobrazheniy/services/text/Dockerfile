FROM python:3.11-slim
WORKDIR /app
COPY requirements-svc.txt .
RUN pip install --no-cache-dir -r requirements-svc.txt
COPY common/ common/
COPY services/text/ services/text/
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "services.text.main"]
