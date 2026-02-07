FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

RUN groupadd --system appuser && useradd --system --gid appuser appuser

COPY --from=builder /install /usr/local
WORKDIR /app
COPY app/ app/
COPY templates/ templates/

USER appuser

CMD ["python", "-m", "app"]
