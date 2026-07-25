# =============================================================================
# Coraci Chat — Dockerfile
# =============================================================================
# Chat com IA compatível com API OpenAI
#
# Build:
#   docker build -t coraci-chat -f Dockerfile .
#
# Run:
#   docker run --rm -p 5000:5000 coraci-chat
# =============================================================================

FROM python:3.12-slim

LABEL org.opencontainers.image.title="Coraci Chat"
LABEL org.opencontainers.image.description="Chat com IA — interface web compatível com OpenAI API"
LABEL org.opencontainers.image.version="1.0.0"

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Dependências do sistema
RUN apt-get update -qq && apt-get install -y -qq \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY app.py config.json ./
COPY templates/ ./templates/
COPY static/ ./static/

# Porta
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:5000/ || exit 1

# Entrypoint
CMD ["python3", "app.py", "--host", "0.0.0.0", "--port", "5000"]
