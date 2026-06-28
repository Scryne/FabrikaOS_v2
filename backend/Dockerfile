# FabrikaOS API imajı
# NOT (S1): tek aşamalı, dev bağımlılıkları dahil (container içi test için).
# Faz 5'te çok aşamalı/sertleştirilmiş prod imajına ayrılacak.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/code/backend

WORKDIR /code

# Proje meta + kaynak (hatchling wheel'i backend/app'ten üretir)
COPY pyproject.toml README.md ./
COPY backend/ ./backend/

RUN pip install --upgrade pip && pip install ".[dev]"

EXPOSE 8000

# Prod komutu; dev'de docker-compose.override.yml --reload ile değiştirir.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
