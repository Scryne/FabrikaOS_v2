# ADR-0001: Backend dili ve çerçevesi

Durum: Kabul
Tarih: 2026-06-29

## Bağlam
Platform; zengin AI/ML yetenekleri, yüksek eşzamanlı I/O (saha verisi, WebSocket) ve
hızlı API geliştirme gerektiriyor. Adaylar: Python/FastAPI, Node/NestJS, Go, Java/Spring.

## Karar
Backend **Python 3.12 + FastAPI** (async, ASGI) ile geliştirilir; Pydantic v2 ile
doğrulama, Uvicorn/Gunicorn ile sunum.

## Sonuçlar
- (+) AI/ML ekosistemi doğrudan Python'da (scikit-learn, pandas) — Faz 3 için kritik.
- (+) API-first, otomatik OpenAPI/Swagger, async I/O.
- (+) Hızlı geliştirme; küçük ekip için düşük operasyon riski.
- (−) CPU-yoğun işler için Celery worker'lara devredilir (GIL etkisi yönetilir).
