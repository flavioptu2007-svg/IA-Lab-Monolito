"""Rotas do LeituraIA Brasil (MVP) — prefixo ``/api/leituraia``.

Inclui também a página do Leitor Digital acessível (``/leituraia/leitor/{id}``),
servida como HTML, com controles de tamanho de fonte e alto contraste.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from leituraia import config
from leituraia.auth import (
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    get_current_user,
    get_user_store,
)
from leituraia.generator import gerar_texto
from leituraia.library import get_library
from leituraia.models import (
    DashboardOut,
    GerarTextoRequest,
    LeituraRegistro,
    LoginRequest,
    NIVEL_ROTULO,
    RegistroRequest,
    TextoCreate,
    TextoGerado,
    TextoOut,
    TokenPair,
    UsuarioOut,
)
from leituraia.rbac import require

router = APIRouter(prefix="/api/leituraia", tags=["leituraia"])
leitor_pages = APIRouter(tags=["leituraia-leitor"])


# ── Autenticação ─────────────────────────────────────────────────────
@router.post("/auth/registro", response_model=TokenPair, status_code=201)
def registrar(dados: RegistroRequest) -> TokenPair:
    try:
        usuario = get_user_store().criar(
            dados.nome, dados.email, dados.senha, dados.perfil
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _token_par(usuario)


@router.post("/auth/login", response_model=TokenPair)
def login(dados: LoginRequest) -> TokenPair:
    usuario = get_user_store().autenticar(dados.email, dados.senha)
    if usuario is None:
        raise HTTPException(401, "email ou senha incorretos")
    return _token_par(usuario)


@router.post("/auth/refresh", response_model=TokenPair)
def refresh(refresh_token: str = Query(...)) -> TokenPair:
    payload = decodificar_token(refresh_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(401, "refresh token invalido ou expirado")
    usuario = get_user_store().por_id(payload["sub"])
    if usuario is None:
        raise HTTPException(401, "usuario nao encontrado")
    return _token_par(usuario)


@router.get("/auth/me", response_model=UsuarioOut)
def me(usuario=Depends(get_current_user)) -> UsuarioOut:
    return _saida_usuario(usuario)


# ── Gerador IA ───────────────────────────────────────────────────────
@router.post("/textos/gerar", response_model=TextoGerado)
def gerar(dados: GerarTextoRequest, _=Depends(require("textos:gerar"))) -> TextoGerado:
    return gerar_texto(dados)


# ── Biblioteca ───────────────────────────────────────────────────────
@router.get("/biblioteca", response_model=list[TextoOut])
def listar_biblioteca(
    disciplina: str | None = None,
    ano: str | None = None,
    tema: str | None = None,
    nivel: str | None = None,
    tipo: str | None = None,
    genero: str | None = None,
    idioma: str | None = None,
    tags: str | None = None,
    bncc: str | None = None,
    crmg: str | None = None,
    palavras_min: int | None = None,
    palavras_max: int | None = None,
    tempo_min: int | None = None,
    tempo_max: int | None = None,
    _=Depends(require("textos:ler")),
) -> list[TextoOut]:
    return get_library().listar(
        disciplina=disciplina,
        ano=ano,
        tema=tema,
        nivel=nivel,
        tipo=tipo,
        genero=genero,
        idioma=idioma,
        tags=tags,
        bncc=bncc,
        crmg=crmg,
        palavras_min=palavras_min,
        palavras_max=palavras_max,
        tempo_min=tempo_min,
        tempo_max=tempo_max,
    )


@router.get("/biblioteca/{texto_id}", response_model=TextoOut)
def obter_texto(texto_id: str, _=Depends(require("textos:ler"))) -> TextoOut:
    texto = get_library().obter(texto_id)
    if texto is None:
        raise HTTPException(404, "texto nao encontrado")
    return texto


@router.post("/biblioteca", response_model=TextoOut, status_code=201)
def criar_texto(dados: TextoCreate, _=Depends(require("biblioteca:gerenciar"))) -> TextoOut:
    return get_library().criar(dados)


@router.delete("/biblioteca/{texto_id}", status_code=204)
def remover_texto(texto_id: str, _=Depends(require("biblioteca:gerenciar"))):
    if not get_library().deletar(texto_id):
        raise HTTPException(404, "texto nao encontrado")


# ── Leitura ──────────────────────────────────────────────────────────
@router.get("/biblioteca/{texto_id}/leitura", response_model=dict)
def payload_leitura(
    texto_id: str, _=Depends(require("textos:ler"))
) -> dict:
    texto = get_library().obter(texto_id)
    if texto is None:
        raise HTTPException(404, "texto nao encontrado")
    return {
        "id": texto.id,
        "titulo": texto.titulo,
        "conteudo": texto.conteudo,
        "glossario": texto.glossario,
        # Sem as respostas: o gabarito é controlado pelo professor.
        "perguntas": [{"pergunta": p.pergunta, "tipo": p.tipo} for p in texto.perguntas],
        "palavras": texto.palavras,
        "tempo_leitura_min": texto.tempo_leitura_min,
        "nivel": NIVEL_ROTULO.get(texto.nivel, texto.nivel),
        "ano": texto.ano,
        "disciplina": texto.disciplina,
        "tema": texto.tema,
    }


@router.post("/biblioteca/{texto_id}/leitura/registro", status_code=201)
def registrar_leitura(
    texto_id: str,
    dados: LeituraRegistro,
    _=Depends(require("leitura:registrar")),
) -> dict:
    if get_library().obter(texto_id) is None:
        raise HTTPException(404, "texto nao encontrado")
    total = get_library().registrar_leitura()
    return {"registrado": True, "total_leituras": total, "completou": dados.completou}


# ── Dashboard ────────────────────────────────────────────────────────
@router.get("/dashboard", response_model=DashboardOut)
def dashboard(_=Depends(require("dashboard:ver"))) -> DashboardOut:
    loja = get_user_store()
    liv = get_library()
    perfis: dict[str, int] = {}
    for u in loja.listar():
        perfis[u.perfil.value] = perfis.get(u.perfil.value, 0) + 1
    professores = sum(
        v for k, v in perfis.items() if k in {"professor", "professor_apoio", "monitor"}
    )
    return DashboardOut(
        alunos=perfis.get("aluno", 0),
        professores=professores,
        leituras=liv.total_leituras,
        textos_biblioteca=liv.total_textos,
        habilidades=liv.habilidades(),
        perfis=perfis,
    )


# ── Página do Leitor Digital (HTML acessível) ────────────────────────
# O texto é renderizado no servidor (sem fetch no cliente): funciona sem
# autenticação, não expõe as respostas do gabarito e é mais rápido.
_LEITOR_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>$titulo — LeituraIA Brasil</title>
<style>
:root{--tinta:#333;--fundo:#faf7f0;--papel:#fffdf8;--acento:#1a5276;--fonte:18px}
body{font-family:Georgia,serif;color:var(--tinta);background:var(--fundo);margin:0;padding:20px;line-height:1.7}
.wrap{max-width:720px;margin:0 auto}
header{border-bottom:2px solid var(--acento);padding-bottom:12px;margin-bottom:20px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center}
h1{font-size:1.6em;margin:0;color:var(--acento)}
.meta{font-size:.9em;color:#666}
.controles{display:flex;gap:8px;flex-wrap:wrap}
.controles button,.controles a{font-size:.9em;padding:6px 12px;border:1px solid #999;border-radius:6px;background:#fff;cursor:pointer;text-decoration:none;color:var(--tinta)}
.controles button:hover,.controles a:hover{background:#eee}
article{background:var(--papel);padding:28px 30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.08);font-size:var(--fonte)}
article p{margin:0 0 1em;text-align:justify}
.glossario{background:#eef4f8;border-left:5px solid var(--acento);padding:12px 16px;border-radius:0 8px 8px 0;margin:18px 0;font-size:.92em}
.perguntas{margin-top:22px}
.perguntas h3{color:var(--acento)}
.perguntas li{margin-bottom:10px}
.alto-contraste{--tinta:#fff;--fundo:#000;--papel:#111;--acento:#ffd54f}
.alto-contraste .glossario{background:#1a1a1a;border-color:var(--acento)}
.alto-contraste header{border-color:var(--acento)}
@media print{body{background:#fff}article{box-shadow:none;padding:0}.controles{display:none}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div><h1>📖 Leitor Digital</h1><div class="meta">$meta</div></div>
    <div class="controles">
      <button onclick="fonte(2)">A+</button>
      <button onclick="fonte(0)">A</button>
      <button onclick="fonte(-2)">A−</button>
      <button onclick="document.body.classList.toggle('alto-contraste')">◐ Alto contraste</button>
      <button onclick="window.print()">🖨️</button>
    </div>
  </header>
  <article>
    <h2>$titulo_h2</h2>
    $paragrafos
    $glossario
    $perguntas
  </article>
</div>
<script>
function fonte(delta){
  const r=document.documentElement;
  const atual=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--fonte'))||18;
  const novo=Math.min(30,Math.max(14,atual+delta));
  r.style.setProperty('--fonte', novo+'px');
}
</script>
</body>
</html>
"""


@leitor_pages.get("/leituraia/leitor/{texto_id}", response_class=HTMLResponse)
def leitor_html(texto_id: str) -> HTMLResponse:
    texto = get_library().obter(texto_id)
    if texto is None:
        raise HTTPException(404, "texto nao encontrado")
    import html as _html

    paragrafos = "".join(
        f"<p>{_html.escape(p)}</p>"
        for p in texto.conteudo.split("\n\n")
        if p.strip()
    )
    glossario = (
        f"<div class='glossario'><b>Glossário:</b> "
        f"{_html.escape(' · '.join(texto.glossario))}</div>"
        if texto.glossario
        else ""
    )
    perguntas = "".join(
        f"<li>{_html.escape(p.pergunta)}</li>" for p in texto.perguntas
    )
    perguntas_html = (
        "<div class='perguntas'><h3>Perguntas de compreensão leitora</h3>"
        f"<ol>{perguntas}</ol></div>"
        if perguntas
        else ""
    )
    meta = (
        f"{_html.escape(texto.disciplina)} · {texto.ano}º ano · "
        f"{_html.escape(texto.tema)} · Nível: {NIVEL_ROTULO.get(texto.nivel, texto.nivel)} · "
        f"{texto.palavras} palavras · ~{texto.tempo_leitura_min} min de leitura"
    )
    from string import Template as _Template

    pagina = _Template(_LEITOR_HTML).safe_substitute(
        titulo=_html.escape(texto.titulo),
        meta=_html.escape(meta),
        titulo_h2=_html.escape(texto.titulo),
        paragrafos=paragrafos,
        glossario=glossario,
        perguntas=perguntas_html,
    )
    return HTMLResponse(pagina)


# ── Helpers ──────────────────────────────────────────────────────────
def _saida_usuario(usuario) -> UsuarioOut:
    return UsuarioOut(id=usuario.uid, nome=usuario.nome, email=usuario.email, perfil=usuario.perfil)


def _token_par(usuario) -> TokenPair:
    return TokenPair(
        access_token=criar_access_token(usuario.uid, usuario.perfil.value),
        refresh_token=criar_refresh_token(usuario.uid, usuario.perfil.value),
        usuario=_saida_usuario(usuario),
    )
