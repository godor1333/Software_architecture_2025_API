FROM python:3.12-slim
WORKDIR /app
ENV PIP_DEFAULT_TIMEOUT=180 PIP_RETRIES=5
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch==2.14.1+cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8012
CMD ["uvicorn", "api:api", "--host", "0.0.0.0", "--port", "8012"]
