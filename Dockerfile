# =============================================================================
# IA-Lab Enterprise — Dockerfile
# =============================================================================
# Multi-stage build otimizado:
#   1. builder: instala dependências Python via pyproject.toml
#   2. runtime: imagem final enxuta com apenas o necessário
#
# Build:
#   docker build -t ia-lab-enterprise .
#
# Run:
#   docker run --rm -p 8000:8000 ia-lab-enterprise
#
# Com Qdrant (RAG):
#   docker run --rm -p 8000:8000 \
#     -e QDRANT_HOST=host.docker.internal \
#     ia-lab-enterprise
# =============================================================================

# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Only copy dependency files (leverage Docker cache)
COPY pyproject.toml requirements.txt ./

# Install build deps + project dependencies
RUN pip install --no-cache-dir build wheel && \
    pip install --no-cache-dir --prefix=/install ".[dev]"

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="IA-Lab Enterprise"
LABEL org.opencontainers.image.description="Plataforma profissional de IA local com pipeline de áudio, agentes e API REST"
LABEL org.opencontainers.image.version="0.1.0"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# System dependencies (minimal)
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --ingroup app --no-create-home app

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code (selective — only what's needed)
COPY ai/ ./ai/
COPY api/ ./api/
COPY web/ ./web/
COPY src/ ./src/
COPY leituraia/ ./leituraia/
COPY Aplicativo_Coraci/ ./Aplicativo_Coraci/
# Create data directories
RUN mkdir -p /data /tmp/ia-lab-audio /app/data && \
    chown -R app:app /app /data /tmp/ia-lab-audio

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

# Default: start FastAPI server
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
