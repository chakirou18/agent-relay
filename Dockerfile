FROM python:3.11-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    RELAY_DATABASE_URL=sqlite:////data/agent-relay.db
WORKDIR /app
RUN groupadd --gid 10001 relay \
    && useradd --uid 10001 --gid relay --no-create-home relay \
    && mkdir /data && chown relay:relay /data
COPY --from=builder /app/.venv /app/.venv
COPY main.py database.py storage.py schemas.py errors.py dashboard.py dashboard.html ./
USER relay
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
