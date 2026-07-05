FROM python:3.11-slim AS builder

# Grab the standalone uv binary rather than pip-installing it.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Copy dependency files first for layer caching, install deps before app code.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-group dev

COPY backend/ ./backend/
RUN uv sync --frozen --no-group dev

ENV PATH="/app/.venv/bin:${PATH}"

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Create non-root user
RUN addgroup --system rapp && adduser --system --ingroup rapp rapp

WORKDIR /app

# Copy the uv-managed virtualenv and application code from the builder stage
COPY --from=builder /app/.venv /app/.venv
COPY backend/ ./backend/

# Data directory for ChromaDB persistence
RUN mkdir -p /app/data/chroma_db && chown -R rapp:rapp /app

USER rapp

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000

# Production: Gunicorn with uvicorn workers
CMD ["gunicorn", "backend.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
