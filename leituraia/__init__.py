"""LeituraIA Brasil — MVP de plataforma de compreensão leitora com IA.

Módulos:
- ``config``: configuração por ambiente (endpoint/modelo/chave/JWT).
- ``rbac``: 11 perfis e matriz de permissões.
- ``auth``: JWT (access + refresh) e hash de senha.
- ``models``: schemas Pydantic.
- ``generator``: gerador de textos didáticos (IA com fallback offline).
- ``library``: biblioteca de textos com filtros (acervo semeado).
- ``routes``: rotas FastAPI (``/api/leituraia`` + Leitor Digital HTML).
"""

from __future__ import annotations

__version__ = "0.1.0"

from leituraia.auth import UserStore, get_user_store
from leituraia.library import LibraryStore, get_library
from leituraia.rbac import Profile, PERMISSIONS, require, tem_permissao

__all__ = [
    "__version__",
    "Profile",
    "PERMISSIONS",
    "require",
    "tem_permissao",
    "UserStore",
    "get_user_store",
    "LibraryStore",
    "get_library",
]
