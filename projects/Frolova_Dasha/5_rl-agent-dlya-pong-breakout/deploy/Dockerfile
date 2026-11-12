FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libsdl2-2.0-0 gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY tests ./tests
COPY scripts ./scripts
COPY deploy/init.sql /deploy/init.sql

RUN mkdir -p /models
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1
