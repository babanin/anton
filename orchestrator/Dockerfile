FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN groupadd --system appuser && useradd --system --gid appuser appuser

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app/ app/
COPY templates/ templates/
RUN uv sync --frozen --no-dev --no-editable

USER appuser

CMD ["uv", "run", "python", "-m", "app"]
