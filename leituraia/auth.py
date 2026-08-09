"""Autenticação do LeituraIA Brasil — JWT + refresh token + RBAC.

- Senhas: PBKDF2-HMAC-SHA256 (stdlib, sem dependências externas).
- Tokens: HS256 (python-jose) — access curto (30 min) + refresh (7 dias).
- Usuários: armazenamento em memória (padrão do monolito); a persistência
  em PostgreSQL é uma evolução natural (schema já desenhado nos models).

O módulo expõe ``get_current_user`` como dependência do FastAPI, usada
pelo ``leituraia.rbac.require`` para o controle de permissões.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from leituraia import config
from leituraia.rbac import Profile

_bearer = HTTPBearer(auto_error=False)

_PBKDF2_ITERATIONS = 200_000


# ── Hash de senha (PBKDF2) ───────────────────────────────────────────
def hash_senha(senha: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verificar_senha(senha: str, armazenada: str) -> bool:
    try:
        _, iters, salt_hex, hash_hex = armazenada.split("$")
        salt = bytes.fromhex(salt_hex)
        esperado = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, int(iters))
        return hmac.compare_digest(dk, esperado)
    except (ValueError, TypeError):
        return False


# ── Tokens JWT ───────────────────────────────────────────────────────
def _gerar_token(sub: str, perfil: str, exp: datetime) -> str:
    from jose import jwt

    payload = {
        "sub": sub,
        "perfil": perfil,
        "iat": int(time.time()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, config.get_jwt_secret(), algorithm="HS256")


def criar_access_token(uid: str, perfil: str) -> str:
    return _gerar_token(uid, perfil, datetime.now(timezone.utc) + timedelta(minutes=30))


def criar_refresh_token(uid: str, perfil: str) -> str:
    return _gerar_token(uid, perfil, datetime.now(timezone.utc) + timedelta(days=7))


def decodificar_token(token: str) -> dict | None:
    from jose import jwt, JWTError

    try:
        return jwt.decode(token, config.get_jwt_secret(), algorithms=["HS256"])
    except JWTError:
        return None


# ── Usuários (em memória) ────────────────────────────────────────────
@dataclass
class Usuario:
    uid: str
    nome: str
    email: str
    perfil: Profile
    senha_hash: str
    criado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class UserStore:
    def __init__(self) -> None:
        self._por_id: dict[str, Usuario] = {}
        self._por_email: dict[str, Usuario] = {}

    def criar(self, nome: str, email: str, senha: str, perfil: Profile) -> Usuario:
        email = email.strip().lower()
        if email in self._por_email:
            raise ValueError("email ja cadastrado")
        u = Usuario(
            uid=str(uuid.uuid4()),
            nome=nome.strip(),
            email=email,
            perfil=perfil,
            senha_hash=hash_senha(senha),
        )
        self._por_id[u.uid] = u
        self._por_email[u.email] = u
        return u

    def autenticar(self, email: str, senha: str) -> Usuario | None:
        u = self._por_email.get(email.strip().lower())
        if u and verificar_senha(senha, u.senha_hash):
            return u
        return None

    def por_id(self, uid: str) -> Usuario | None:
        return self._por_id.get(uid)

    def listar(self) -> list[Usuario]:
        return sorted(self._por_id.values(), key=lambda u: u.nome.lower())

    @property
    def total(self) -> int:
        return len(self._por_id)


_user_store: UserStore | None = None


def get_user_store() -> UserStore:
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store


# ── Dependências FastAPI ─────────────────────────────────────────────
def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Usuario:
    if cred is None or cred.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "autenticacao requerida")
    payload = decodificar_token(cred.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token invalido ou expirado")
    usuario = get_user_store().por_id(payload["sub"])
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "usuario nao encontrado")
    return usuario


__all__ = [
    "Usuario",
    "UserStore",
    "get_user_store",
    "hash_senha",
    "verificar_senha",
    "criar_access_token",
    "criar_refresh_token",
    "decodificar_token",
    "get_current_user",
]
