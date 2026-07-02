FROM python:3.11-slim AS builder

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock* ./

# Export deps to requirements format and install into a clean venv
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-interaction --no-ansi

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Create non-root user
RUN addgroup --system rapp && adduser --system --ingroup rapp rapp

WORKDIR /app

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ ./backend/

# Data directory for ChromaDB persistence
RUN mkdir -p /app/data/chroma_db && chown -R rapp:rapp /app

USER rapp

EXPOSE 8000

# Production: Gunicorn with uvicorn workers
CMD ["gunicorn", "backend.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
