"""Telemetria: logging estruturado e métricas Prometheus."""

from __future__ import annotations

import logging
import sys

from prometheus_client import Counter, Gauge, Histogram

# ---- Métricas Prometheus ----

health_status = Gauge(
    "ia_lab_component_health",
    "Estado de saúde dos componentes do sistema (1=ok, 0=erro)",
    ["component"],
)

request_counter = Counter(
    "ia_lab_requests_total", "Total de requisições de chat", ["provider", "task_type", "status"]
)

request_duration = Histogram(
    "ia_lab_request_duration_seconds",
    "Duração das requisições em segundos",
    ["provider", "task_type"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

active_providers = Gauge("ia_lab_active_providers", "Número de provedores configurados e ativos")


# ---- Logger estruturado ----


def get_logger(name: str = "ia-lab") -> logging.Logger:
    """Retorna um logger configurado com o nível do settings."""
    from ai.settings import settings

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False

    return logger
