"""Wrapper fino sobre o CLI do rclone, com retry/backoff para rate limit."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from typing import Any

from src.drive_audit.config import REMOTE

RATE_LIMIT_MARKERS = (
    "rate_limit_exceeded",
    "ratelimitexceeded",
    "userratelimitexceeded",
    "quotaexceeded",
)


class RcloneError(RuntimeError):
    """Falha definitiva de um comando rclone."""


def run_rclone(
    args: list[str],
    *,
    retries: int = 5,
    base_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Executa ``rclone <args>``; repete só em erros de cota/rate limit."""
    cmd = ["rclone", *args]
    last = ""
    for attempt in range(retries):
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return proc.stdout
        stderr = proc.stderr or ""
        last = stderr.strip() or (proc.stdout or "").strip()
        if any(marker in stderr.lower() for marker in RATE_LIMIT_MARKERS) and attempt < retries - 1:
            sleep(base_delay * (2**attempt))
            continue
        raise RcloneError(f"rclone {' '.join(args)} falhou: {last}")
    raise RcloneError(f"rclone {' '.join(args)} esgotou os retries: {last}")


def lsjson(remote_path: str = REMOTE, *, recursive: bool = True) -> list[dict[str, Any]]:
    """Lista itens com metadados e hashes (``--hash``)."""
    args = ["lsjson", remote_path, "--hash"]
    if recursive:
        args.append("-R")
    data = json.loads(run_rclone(args) or "[]")
    if not isinstance(data, list):
        raise RcloneError("lsjson retornou JSON inesperado (esperava uma lista)")
    return data


def hashsum(remote_path: str, hasher: str = "MD5") -> str:
    """Calcula o hash de um caminho específico (fallback; lento)."""
    return run_rclone(["hashsum", hasher, remote_path]).strip()
