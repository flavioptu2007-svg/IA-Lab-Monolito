"""Testes do módulo LeituraIA Brasil (MVP).

Cobre: fluxo de autenticação (registro/login/refresh/me), RBAC por perfil,
gerador de textos (modo template offline), biblioteca com filtros, leitor e
dashboard.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from leituraia import get_library
from leituraia.auth import hash_senha, verificar_senha


@pytest.fixture(scope="module")
def client():
    from api.server import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """Força o modo template: nenhuma chamada real de IA nos testes."""
    monkeypatch.setenv("LEITURAIA_OFFLINE", "1")
    monkeypatch.setenv("LEITURAIA_API_KEY", "")


def _registrar(client: TestClient, perfil: str = "aluno", email: str | None = None):
    payload = {
        "nome": f"Usuário {perfil}",
        "email": email or f"{perfil}@teste.com",
        "senha": "senha123",
        "perfil": perfil,
    }
    resp = client.post("/api/leituraia/auth/registro", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _token(resp_json: dict) -> str:
    return resp_json["access_token"]


def _auth(resp_json: dict) -> dict:
    return {"Authorization": f"Bearer {_token(resp_json)}"}


# ── Senhas ───────────────────────────────────────────────────────────
def test_hash_e_verificacao_de_senha():
    h = hash_senha("senha123")
    assert h.startswith("pbkdf2$")
    assert verificar_senha("senha123", h)
    assert not verificar_senha("outra", h)
    assert not verificar_senha("senha123", "formato-invalido")


# ── Autenticação ─────────────────────────────────────────────────────
def test_registro_e_login(client):
    dados = _registrar(client, "professor", "prof@teste.com")
    assert dados["token_type"] == "bearer"
    assert dados["usuario"]["perfil"] == "professor"

    resp = client.post(
        "/api/leituraia/auth/login",
        json={"email": "prof@teste.com", "senha": "senha123"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    resp_errado = client.post(
        "/api/leituraia/auth/login",
        json={"email": "prof@teste.com", "senha": "errada"},
    )
    assert resp_errado.status_code == 401


def test_email_duplicado(client):
    _registrar(client, "diretor", "dir@teste.com")
    resp = client.post(
        "/api/leituraia/auth/registro",
        json={"nome": "Outro", "email": "DIR@teste.com", "senha": "senha123", "perfil": "diretor"},
    )
    assert resp.status_code == 409


def test_refresh_token(client):
    dados = _registrar(client, "coordenador", "coord@teste.com")
    resp = client.post(
        "/api/leituraia/auth/refresh",
        params={"refresh_token": dados["refresh_token"]},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_me_autenticado(client):
    dados = _registrar(client, "monitor", "monitor@teste.com")
    resp = client.get("/api/leituraia/auth/me", headers=_auth(dados))
    assert resp.status_code == 200
    assert resp.json()["perfil"] == "monitor"


def test_me_sem_token(client):
    resp = client.get("/api/leituraia/auth/me")
    assert resp.status_code == 401


# ── RBAC ─────────────────────────────────────────────────────────────
def test_aluno_nao_pode_gerar_texto(client):
    aluno = _registrar(client, "aluno", "aluno@teste.com")
    resp = client.post(
        "/api/leituraia/textos/gerar",
        json={"ano": "7", "disciplina": "História", "tema": "Feudalismo"},
        headers=_auth(aluno),
    )
    assert resp.status_code == 403


def test_responsavel_pode_ler_biblioteca(client):
    resp = _registrar(client, "responsavel", "resp@teste.com")
    resp = client.get("/api/leituraia/biblioteca", headers=_auth(resp))
    assert resp.status_code == 200


def test_aluno_nao_gerencia_biblioteca(client):
    aluno = _registrar(client, "aluno", "aluno2@teste.com")
    resp = client.post(
        "/api/leituraia/biblioteca",
        json={
            "titulo": "X",
            "conteudo": "texto de teste com mais de trinta caracteres",
            "ano": "7",
            "disciplina": "História",
            "tema": "T",
        },
        headers=_auth(aluno),
    )
    assert resp.status_code == 403


# ── Gerador (offline) ────────────────────────────────────────────────
def test_gerar_texto_template(client):
    prof = _registrar(client, "professor", "prof2@teste.com")
    resp = client.post(
        "/api/leituraia/textos/gerar",
        json={
            "ano": "7",
            "disciplina": "História",
            "tema": "Feudalismo",
            "palavras": 200,
            "nivel": "fundamental2",
            "objetivo": "Compreensão leitora",
            "bncc": ["EF07HI04"],
        },
        headers=_auth(prof),
    )
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["origem"] == "template"
    assert dados["titulo"]
    assert len(dados["texto"].split()) >= 80
    assert len(dados["glossario"]) >= 3
    assert len(dados["perguntas"]) >= 3
    assert dados["metadados"]["tema"] == "Feudalismo"
    assert dados["metadados"]["bncc"] == ["EF07HI04"]


# ── Biblioteca ───────────────────────────────────────────────────────
def test_biblioteca_semeadas(client):
    prof = _registrar(client, "professor", "prof3@teste.com")
    resp = client.get("/api/leituraia/biblioteca", headers=_auth(prof))
    assert resp.status_code == 200
    textos = resp.json()
    assert len(textos) >= 3
    titulos = [t["titulo"] for t in textos]
    assert any("feudalismo" in t.lower() for t in titulos)
    assert any("Caminha" in t for t in titulos)


def test_biblioteca_filtros(client):
    prof = _registrar(client, "professor", "prof4@teste.com")
    headers = _auth(prof)

    resp = client.get("/api/leituraia/biblioteca", params={"ano": "7"}, headers=headers)
    assert all(t["ano"] == "7" for t in resp.json())

    resp = client.get(
        "/api/leituraia/biblioteca", params={"disciplina": "História"}, headers=headers
    )
    assert all(t["disciplina"] == "História" for t in resp.json())
    assert len(resp.json()) >= 2

    resp = client.get("/api/leituraia/biblioteca", params={"tema": "água"}, headers=headers)
    assert all("água" in t["tema"].lower() for t in resp.json())


def test_criar_e_deletar_texto(client):
    prof = _registrar(client, "professor", "prof5@teste.com")
    headers = _auth(prof)
    resp = client.post(
        "/api/leituraia/biblioteca",
        json={
            "titulo": "Texto novo",
            "conteudo": "Um texto de exemplo criado pelo professor para testar a biblioteca do LeituraIA.",
            "ano": "8",
            "disciplina": "Geografia",
            "tema": "Clima",
            "nivel": "fundamental2",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    novo = resp.json()
    assert novo["palavras"] > 10
    assert novo["tempo_leitura_min"] >= 1

    resp = client.delete(f"/api/leituraia/biblioteca/{novo['id']}", headers=headers)
    assert resp.status_code == 204

    resp = client.get(f"/api/leituraia/biblioteca/{novo['id']}", headers=headers)
    assert resp.status_code == 404


# ── Leitor ───────────────────────────────────────────────────────────
def test_payload_leitura(client):
    prof = _registrar(client, "professor", "prof6@teste.com")
    headers = _auth(prof)
    texto_id = get_library().listar(ano="7", disciplina="História")[0].id
    resp = client.get(f"/api/leituraia/biblioteca/{texto_id}/leitura", headers=headers)
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["palavras"] > 0
    assert dados["tempo_leitura_min"] >= 1
    assert dados["conteudo"]
    # O payload do leitor não deve expor as respostas do gabarito.
    assert all("resposta" not in p for p in dados["perguntas"])


def test_pagina_leitor_html_renderiza_texto(client):
    texto_id = get_library().listar()[0].id
    resp = client.get(f"/leituraia/leitor/{texto_id}")
    assert resp.status_code == 200
    assert "Leitor Digital" in resp.text
    assert "fonte(" in resp.text  # controles de acessibilidade
    # O conteúdo é renderizado no servidor (sem fetch no cliente).
    assert "Glossário" in resp.text
    assert "Perguntas de compreensão" in resp.text
    assert "min de leitura" in resp.text
    # O gabarito (respostas) não aparece na página pública.
    assert "resposta" not in resp.text.lower()


def test_registro_leitura_aluno(client):
    aluno = _registrar(client, "aluno", "aluno3@teste.com")
    texto_id = get_library().listar()[0].id
    antes = get_library().total_leituras
    resp = client.post(
        f"/api/leituraia/biblioteca/{texto_id}/leitura/registro",
        json={"texto_id": texto_id, "tempo_segundos": 90, "completou": True},
        headers=_auth(aluno),
    )
    assert resp.status_code == 201
    assert resp.json()["total_leituras"] == antes + 1


def test_registro_leitura_aluno_sem_permissao_professor_ok(client):
    prof = _registrar(client, "professor", "prof7@teste.com")
    texto_id = get_library().listar()[0].id
    resp = client.post(
        f"/api/leituraia/biblioteca/{texto_id}/leitura/registro",
        json={"texto_id": texto_id, "tempo_segundos": 10},
        headers=_auth(prof),
    )
    assert resp.status_code == 201


# ── Dashboard ────────────────────────────────────────────────────────
def test_dashboard(client):
    prof = _registrar(client, "professor", "prof8@teste.com")
    resp = client.get("/api/leituraia/dashboard", headers=_auth(prof))
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["textos_biblioteca"] >= 3
    assert "alunos" in dados
    assert "habilidades" in dados
    assert dados["professores"] >= 1


def test_dashboard_sem_autenticacao(client):
    resp = client.get("/api/leituraia/dashboard")
    assert resp.status_code == 401
