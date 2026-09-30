"""RBAC do LeituraIA Brasil — 11 perfis e matriz de permissões.

Perfis (do prompt mestre): Administrador, Secretaria de Educação, Diretor,
Supervisor, Especialista, Coordenador Pedagógico, Professor, Professor de
Apoio, Monitor, Aluno e Responsável.

Uso:
    router.get("/x", dependencies=[Depends(require("textos:gerar"))])
"""

from __future__ import annotations

from enum import StrEnum

from fastapi import Depends, HTTPException, status


class Profile(StrEnum):
    ADMIN = "admin"
    SECRETARIA = "secretaria"
    DIRETOR = "diretor"
    SUPERVISOR = "supervisor"
    ESPECIALISTA = "especialista"
    COORDENADOR = "coordenador"
    PROFESSOR = "professor"
    PROFESSOR_APOIO = "professor_apoio"
    MONITOR = "monitor"
    ALUNO = "aluno"
    RESPONSAVEL = "responsavel"


# Conjuntos de perfis "adultos" que têm acesso amplo à plataforma.
_ADULTOS = {
    Profile.ADMIN,
    Profile.SECRETARIA,
    Profile.DIRETOR,
    Profile.SUPERVISOR,
    Profile.ESPECIALISTA,
    Profile.COORDENADOR,
    Profile.PROFESSOR,
    Profile.PROFESSOR_APOIO,
    Profile.MONITOR,
}

# ── Matriz de permissões ─────────────────────────────────────────────
# Cada permissão mapeia para o conjunto de perfis autorizados.
PERMISSIONS: dict[str, set[Profile]] = {
    # Leitura de textos e biblioteca: aberto a todos.
    "textos:ler": _ADULTOS | {Profile.ALUNO, Profile.RESPONSAVEL},
    # Gerar textos com IA: perfis de docência e gestão pedagógica.
    "textos:gerar": _ADULTOS - {Profile.MONITOR},
    # Editar textos: docência e gestão.
    "textos:editar": _ADULTOS - {Profile.MONITOR},
    # Publicar (tornar visível na biblioteca): gestão pedagógica.
    "textos:publicar": {
        Profile.ADMIN,
        Profile.SECRETARIA,
        Profile.DIRETOR,
        Profile.SUPERVISOR,
        Profile.ESPECIALISTA,
        Profile.COORDENADOR,
    },
    # Gerenciar a biblioteca (criar/remover textos).
    "biblioteca:gerenciar": _ADULTOS - {Profile.MONITOR},
    # Ver alunos e turmas.
    "alunos:ver": _ADULTOS,
    # Relatórios de gestão.
    "relatorios:ver": {
        Profile.ADMIN,
        Profile.SECRETARIA,
        Profile.DIRETOR,
        Profile.SUPERVISOR,
        Profile.ESPECIALISTA,
        Profile.COORDENADOR,
    },
    # Dashboard.
    "dashboard:ver": _ADULTOS | {Profile.ALUNO},
    # Registrar uma leitura realizada (aluno).
    "leitura:registrar": {Profile.ALUNO, Profile.PROFESSOR, Profile.MONITOR},
    # Gerenciar usuários (admin/secretaria).
    "usuarios:gerenciar": {Profile.ADMIN, Profile.SECRETARIA},
    # Configurações do sistema.
    "config:gerenciar": {Profile.ADMIN},
}


def tem_permissao(perfil: Profile | str, permissao: str) -> bool:
    perfis = PERMISSIONS.get(permissao)
    if perfis is None:
        return False
    return Profile(perfil) in perfis


def require(permissao: str):
    """Dependency factory do FastAPI — exige o usuário autenticado com a permissão."""
    from leituraia.auth import get_current_user  # import tardio (evita ciclo)

    def _depender(usuario=Depends(get_current_user)) -> object:
        if not tem_permissao(usuario.perfil, permissao):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Perfil '{usuario.perfil}' sem permissão '{permissao}'.",
            )
        return usuario

    return _depender


__all__ = ["Profile", "PERMISSIONS", "tem_permissao", "require"]
