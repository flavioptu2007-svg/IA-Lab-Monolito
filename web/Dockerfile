# =============================================================================
# IA-Lab Web API — Dockerfile
# =============================================================================
# Este Dockerfile constrói apenas o servidor FastAPI.
# Para build completo com dependências, use o Dockerfile raiz.
#
# Build:
#   docker build -t ia-lab-web -f web/Dockerfile .
#
# Run:
#   docker run --rm -p 8000:8000 ia-lab-web
# =============================================================================

FROM python:3.12-slim AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml requirements.txt ./

# Install core dependencies via pyproject.toml (fonte única da verdade)
# Mantenha sincronizado com [project.dependencies] em pyproject.toml
RUN pip install --no-cache-dir --prefix=/install \
    "ia-lab-enterprise[dev]" 2>/dev/null || \
    pip install --no-cache-dir --prefix=/install \
        fastapi>=0.110.0 \
        uvicorn[standard]>=0.29.0 \
        pydantic>=2.0.0 \
        pydantic-settings>=2.0.0 \
        httpx>=0.27.0 \
        prometheus-client>=0.20.0 \
        numpy>=1.26.0

FROM python:3.12-slim

LABEL org.opencontainers.image.title="IA-Lab Web API"
LABEL org.opencontainers.image.description="FastAPI REST API do IA-Lab Enterprise"
LABEL org.opencontainers.image.version="0.1.0"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --ingroup app --no-create-home app

WORKDIR /app

COPY --from=builder /install /usr/local

# Copy only API-related code
COPY api/ ./api/
COPY ai/ ./ai/

RUN mkdir -p /data && chown -R app:app /app /data

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
