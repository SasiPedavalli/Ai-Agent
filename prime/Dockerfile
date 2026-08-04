FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PRIME_ROOT=/app PRIME_RUNTIME_DB_PATH=/data/runtime.db PRIME_DB_PATH=/data/prime.db
WORKDIR /app
COPY . /app
RUN python -m pip install '.[api]' && useradd --create-home --uid 10001 prime && mkdir -p /data && chown -R prime:prime /app /data
USER prime
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
CMD ["prime", "serve", "--host", "0.0.0.0", "--port", "8080"]
