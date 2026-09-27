"""Autenticação por API key e validação anti-SSRF para os routers do monolito.

A API é local-first (painel Vite, portal escolar, Ollama/LM Studio) e não usa
cookies nem sessão. Quando ``IA_LAB_API_TOKEN`` está definido, todo router
protegido exige o header ``X-API-Key``; quando está vazio, a autenticação fica
desabilitada — útil em desenvolvimento local e na suíte de testes — e um aviso
é registrado no boot (ver :func:`warn_if_auth_disabled`).
"""

from __future__ import annotations

import hmac
import ipaddress
import logging
import socket
from urllib.parse import urlparse

from fastapi import Header, HTTPException, status

from ai.settings import settings

logger = logging.getLogger(__name__)

# Header exigido quando um token está configurado.
API_KEY_HEADER = "X-API-Key"

# Hosts que devolvem credenciais de instância em clouds — nunca são providers.
_METADATA_HOSTS = frozenset({"metadata.google.internal", "metadata.goog", "instance-data"})

# IPs de metadata de AWS/GCP/Azure/Alibaba/OpenStack.
_METADATA_IPS = frozenset(
    ipaddress.ip_address(addr)
    for addr in ("169.254.169.254", "169.254.170.2", "100.100.100.200", "fd00:ec2::254")
)


def auth_enabled() -> bool:
    """Indica se a autenticação por API key está ativa (token configurado)."""
    return bool(settings.api_token.get_secret_value())


def warn_if_auth_disabled() -> None:
    """Registra um aviso quando a API sobe sem ``IA_LAB_API_TOKEN``."""
    if not auth_enabled():
        logger.warning(
            "IA_LAB_API_TOKEN não configurado — os routers /api/v2 estão SEM "
            "autenticação. Defina um token (ex.: `openssl rand -hex 32`) antes "
            "de expor a API fora de localhost."
        )


def require_api_key(x_api_key: str = Header(default="", alias=API_KEY_HEADER)) -> None:
    """Dependência do FastAPI: exige ``X-API-Key`` quando há token configurado.

    Sem token configurado a checagem é ignorada (dev local / suíte de testes).
    A comparação usa ``hmac.compare_digest`` para não vazar o token por timing.
    """
    expected = settings.api_token.get_secret_value()
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key ausente ou inválida",
            headers={"WWW-Authenticate": API_KEY_HEADER},
        )


def _resolved_ips(host: str) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve ``host`` para endereços IP; devolve conjunto vazio se não resolver."""
    ips: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, OSError, UnicodeError):
        return ips
    for info in infos:
        address = str(info[4][0]).split("%", 1)[0]  # remove zone-id (ex.: fe80::1%eth0)
        try:
            ips.add(ipaddress.ip_address(address))
        except ValueError:  # pragma: no cover — getaddrinfo sempre devolve IP válido
            continue
    return ips


def validate_api_base_url(url: str) -> str:
    """Valida a URL de um provider antes de usá-la numa requisição server-side.

    Bloqueia sempre: esquemas não-HTTP(S), hosts de metadata de cloud e
    endereços link-local. Bloqueia também loopback/rede privada quando
    ``IA_LAB_ALLOW_PRIVATE_API_HOSTS=false`` (default ``true`` porque o projeto
    é local-first: Ollama/LM Studio na própria máquina e portal na LAN).
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="api_base_url vazia")

    candidate = url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Esquema inválido em api_base_url: {parsed.scheme or '(vazio)'} — use http ou https"
            ),
        )

    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="api_base_url sem host")

    if host.lower().rstrip(".") in _METADATA_HOSTS:
        raise HTTPException(status_code=400, detail="Host de metadata de cloud bloqueado (SSRF)")

    for ip in _resolved_ips(host):
        if ip in _METADATA_IPS or ip.is_link_local:
            raise HTTPException(
                status_code=400,
                detail=f"Destino de metadata/link-local bloqueado (SSRF): {ip}",
            )
        if not settings.allow_private_api_hosts and (
            ip.is_private or ip.is_loopback or ip.is_reserved
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Host privado/loopback bloqueado por "
                    f"IA_LAB_ALLOW_PRIVATE_API_HOSTS=false: {ip}"
                ),
            )

    return candidate
