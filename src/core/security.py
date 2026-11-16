"""Autenticação por API key e validação anti-SSRF para os routers do monolito.

A API é local-first (painel Vite, portal escolar, Ollama/LM Studio) e não usa
cookies nem sessão. Quando ``IA_LAB_API_TOKEN`` está definido, todo router
protegido exige o header ``X-API-Key`` — inclusive as rotas legadas ``/api/*``
de ``api/server.py``. As exceções são os health checks e as duas rotas que o
portal dos alunos chama sem chave (chat e TTS), que ficam sob limite de taxa
(ver :func:`public_access`); quando está vazio, a autenticação fica
desabilitada — útil em desenvolvimento local e na suíte de testes — e um aviso
é registrado no boot (ver :func:`warn_if_auth_disabled`).
"""

from __future__ import annotations

import hmac
import ipaddress
import logging
import math
import socket
import threading
import time
from collections import deque
from urllib.parse import urlparse

from fastapi import Header, HTTPException, Request, status

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
            "IA_LAB_API_TOKEN não configurado — as rotas /api e /api/v2 estão SEM "
            "autenticação nem limite de taxa. Defina um token (ex.: `openssl rand -hex 32`) antes "
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


class SlidingWindowLimiter:
    """Limite de requisições por janela deslizante, em memória e por processo.

    Suficiente para uma instância única (Render free, LAN escolar). Com várias
    réplicas cada uma conta em separado — aí o limite passa a ser por réplica.

    A memória é limitada a ``max_keys`` chaves. Se a tabela lotar de chaves
    ainda ativas, as chaves novas passam a dividir um único contador de
    transbordo: nenhum contador ativo é descartado, então lotar a tabela não
    zera o limite de ninguém.
    """

    OVERFLOW_KEY = "__overflow__"

    def __init__(self, window_seconds: float = 60.0, max_keys: int = 10_000) -> None:
        self.window = window_seconds
        self.max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, now: float | None = None) -> float:
        """Registra um acesso. Devolve 0 se permitido ou os segundos até liberar."""
        if limit <= 0:
            return 0.0
        now = time.monotonic() if now is None else now
        cutoff = now - self.window
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                if len(self._hits) >= self.max_keys:
                    self._prune(cutoff)
                if len(self._hits) >= self.max_keys:
                    key = self.OVERFLOW_KEY
                hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return max(hits[0] + self.window - now, 0.001)
            hits.append(now)
            return 0.0

    def _prune(self, cutoff: float) -> None:
        """Descarta só as chaves sem nenhum acesso dentro da janela."""
        stale = [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]
        for k in stale:
            del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class PublicLimiter:
    """Limites do acesso anônimo: um contador por IP e um contador global.

    Ficam em tabelas separadas para que a rotatividade de IPs nunca afete o
    contador global. O limite por IP é conferido primeiro: assim as tentativas
    barradas de um único IP abusivo não consomem a cota global dos demais.
    """

    def __init__(self) -> None:
        self.per_ip = SlidingWindowLimiter()
        self.total = SlidingWindowLimiter(max_keys=1)

    def check(self, ip: str, ip_limit: int, global_limit: int) -> float:
        wait = self.per_ip.check(ip, ip_limit)
        if wait:
            return wait
        return self.total.check("global", global_limit)

    def reset(self) -> None:
        self.per_ip.reset()
        self.total.reset()


public_limiter = PublicLimiter()


def client_ip(request: Request) -> str:
    """IP do cliente para o limite de taxa.

    Com ``trusted_proxy_hops = N > 0`` usa o N-ésimo valor de X-Forwarded-For
    contado a partir da direita: cada proxy confiável acrescenta à direita o
    endereço de quem se conectou a ele, e tudo à esquerda disso veio do cliente
    e pode ser forjado. Se o header tiver menos valores que N, cai no endereço
    da conexão.
    """
    hops = settings.trusted_proxy_hops
    if hops > 0:
        parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",")]
        parts = [p for p in parts if p]
        if len(parts) >= hops:
            return parts[-hops]
    return request.client.host if request.client else "desconhecido"


def public_access(
    request: Request,
    x_api_key: str = Header(default="", alias=API_KEY_HEADER),
) -> bool:
    """Dependência das rotas que o portal chama sem chave (chat e TTS).

    Devolve ``True`` quando a chamada é anônima — o handler usa isso para
    aplicar limites de tamanho. Regras, com token configurado:

    - ``X-API-Key`` válida: acesso pleno, sem limite de taxa;
    - ``X-API-Key`` inválida: 401 (chave errada não vira acesso anônimo);
    - sem chave: permitido, mas com limite por IP e limite global por minuto.

    Sem token configurado nada é checado (dev local / suíte de testes).
    """
    expected = settings.api_token.get_secret_value()
    if not expected:
        return False
    if x_api_key:
        if hmac.compare_digest(x_api_key, expected):
            return False
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key ausente ou inválida",
            headers={"WWW-Authenticate": API_KEY_HEADER},
        )

    wait = public_limiter.check(
        client_ip(request),
        settings.public_rate_limit_per_minute,
        settings.public_rate_limit_global_per_minute,
    )
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas requisições. Aguarde um pouco e tente de novo.",
            headers={"Retry-After": str(math.ceil(wait))},
        )
    return True


def enforce_public_text_limit(is_public: bool, text: str) -> None:
    """Recusa texto longo demais em chamada anônima (413)."""
    limit = settings.public_max_prompt_chars
    if is_public and limit > 0 and len(text) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Texto acima do limite de {limit} caracteres para acesso sem chave.",
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
