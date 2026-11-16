"""Autenticação das rotas legadas ``/api/*`` e acesso anônimo limitado (chat/TTS).

Cobre:
- sem ``IA_LAB_API_TOKEN`` nada muda (dev local / suíte de testes);
- com token, as rotas administrativas exigem ``X-API-Key``;
- health checks continuam abertos (o orquestrador não envia chave);
- ``POST /api/chat`` e ``POST /api/audio/tts`` — usadas sem chave pelo portal
  dos alunos — aceitam chamada anônima, mas com limite por IP, limite global e
  limite de tamanho do texto; chave válida passa sem limite, chave errada é 401.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from ai.settings import settings
from src.core import security
from src.core.security import SlidingWindowLimiter

TOKEN = "token-de-teste-123"
KEY = {"X-API-Key": TOKEN}

OPEN_PATHS = ("/api/health/live", "/api/health")

# (método, caminho) — tudo que não é health nem rota pública do portal.
PROTECTED_ROUTES = (
    ("GET", "/api/providers"),
    ("GET", "/api/agents"),
    ("GET", "/api/history"),
    ("DELETE", "/api/history"),
    ("GET", "/api/metrics"),
    ("GET", "/api/config"),
    ("GET", "/api/audio/status"),
    ("GET", "/api/audio/devices"),
    ("POST", "/api/audio/record"),
    ("POST", "/api/audio/effects"),
    ("POST", "/api/audio/stt"),
    ("GET", "/api/audio/mic/status"),
    ("POST", "/api/audio/mic/create"),
    ("POST", "/api/audio/mic/remove"),
    ("GET", "/api/audio/metrics"),
    ("GET", "/api/audio/config"),
)


@pytest.fixture
def client() -> TestClient:
    from api.server import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _estado_limpo(monkeypatch):
    """Cada teste começa sem token e com o limitador zerado."""
    monkeypatch.setattr(settings, "api_token", SecretStr(""))
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    security.public_limiter.reset()
    yield
    security.public_limiter.reset()
    import api.server as server

    server.history_store.clear()


@pytest.fixture
def token(monkeypatch) -> str:
    monkeypatch.setattr(settings, "api_token", SecretStr(TOKEN))
    return TOKEN


@pytest.fixture
def chat_ok(monkeypatch):
    """Substitui o AIService: o chat responde sem chamar provider nenhum."""
    import api.server as server

    service = MagicMock()
    service.complete = AsyncMock(return_value="resposta de teste")
    service.choose_provider = MagicMock(return_value="fake")
    monkeypatch.setattr(server, "get_service", lambda: service)
    return service


def _chat(client: TestClient, prompt: str = "Quem foi Tiradentes?", **kwargs):
    return client.post("/api/chat", json={"prompt": prompt, "use_rag": False}, **kwargs)


# ═════════════════════════════════════════════════════════════════════════════
# Cobertura: nenhuma rota legada pode ficar de fora
# ═════════════════════════════════════════════════════════════════════════════


def test_toda_rota_legada_esta_classificada():
    """Rota nova em api/server.py precisa entrar em uma das três listas.

    Evita que um endpoint adicionado depois fique aberto por esquecimento.
    """
    from api.server import app

    conhecidas = (
        {p for _, p in PROTECTED_ROUTES}
        | set(OPEN_PATHS)
        | {"/api/health/ready", "/api/chat", "/api/audio/tts"}
    )
    legadas = {
        r.path
        for r in app.routes
        if getattr(r, "path", "").startswith("/api/")
        and not r.path.startswith("/api/v2/")
        and getattr(r, "endpoint", None) is not None
        and r.endpoint.__module__ == "api.server"
    }
    assert legadas - conhecidas == set(), "rota legada sem regra de acesso definida"


# ═════════════════════════════════════════════════════════════════════════════
# Rotas administrativas
# ═════════════════════════════════════════════════════════════════════════════


class TestRotasProtegidas:
    @pytest.mark.parametrize(("method", "path"), PROTECTED_ROUTES)
    def test_sem_header_devolve_401(self, client, token, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 401, f"{method} {path}"
        assert resp.headers["WWW-Authenticate"] == "X-API-Key"

    @pytest.mark.parametrize(("method", "path"), PROTECTED_ROUTES)
    def test_chave_errada_devolve_401(self, client, token, method, path):
        resp = client.request(method, path, headers={"X-API-Key": "errada"})
        assert resp.status_code == 401, f"{method} {path}"

    @pytest.mark.parametrize("path", ["/api/providers", "/api/history", "/api/config"])
    def test_chave_correta_libera(self, client, token, path):
        assert client.get(path, headers=KEY).status_code == 200

    @pytest.mark.parametrize("path", ["/api/providers", "/api/history", "/api/config"])
    def test_sem_token_configurado_continua_aberto(self, client, path):
        assert client.get(path).status_code == 200

    def test_401_nao_executa_a_acao(self, client, token):
        """DELETE /api/history sem chave não pode apagar nada."""
        import api.server as server

        server.history_store.add(
            server.HistoryEntry(
                id="x", prompt="p", response="r", provider="fake", task_type="general", timestamp=0
            )
        )
        try:
            assert client.delete("/api/history").status_code == 401
            assert len(server.history_store.list()) >= 1
        finally:
            server.history_store.clear()


class TestHealthAberto:
    @pytest.mark.parametrize("path", OPEN_PATHS)
    def test_health_nao_exige_chave(self, client, token, path):
        assert client.get(path).status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# Rotas públicas do portal: chat
# ═════════════════════════════════════════════════════════════════════════════


class TestChatPublico:
    def test_anonimo_e_aceito(self, client, token, chat_ok):
        resp = _chat(client)
        assert resp.status_code == 200, resp.text
        assert resp.json()["response"] == "resposta de teste"

    def test_chave_errada_nao_vira_acesso_anonimo(self, client, token, chat_ok):
        resp = _chat(client, headers={"X-API-Key": "errada"})
        assert resp.status_code == 401
        chat_ok.complete.assert_not_called()

    def test_limite_por_ip(self, client, token, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 3)
        assert [_chat(client).status_code for _ in range(3)] == [200, 200, 200]

        resp = _chat(client)
        assert resp.status_code == 429
        assert int(resp.headers["Retry-After"]) >= 1
        assert chat_ok.complete.call_count == 3, "requisição barrada não pode chegar ao provider"

    def test_chave_valida_nao_sofre_limite(self, client, token, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 1)
        assert _chat(client).status_code == 200
        assert _chat(client).status_code == 429
        assert [_chat(client, headers=KEY).status_code for _ in range(5)] == [200] * 5

    def test_limite_global_vale_para_ips_diferentes(self, client, token, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 100)
        monkeypatch.setattr(settings, "public_rate_limit_global_per_minute", 2)

        codes = [
            _chat(client, headers={"X-Forwarded-For": f"203.0.113.{i}"}).status_code
            for i in range(3)
        ]
        assert codes == [200, 200, 429]

    def test_ips_diferentes_tem_contagens_separadas(self, client, token, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 1)

        a = {"X-Forwarded-For": "203.0.113.10"}
        b = {"X-Forwarded-For": "203.0.113.20"}
        assert _chat(client, headers=a).status_code == 200
        assert _chat(client, headers=a).status_code == 429
        assert _chat(client, headers=b).status_code == 200

    def test_x_forwarded_for_e_ignorado_sem_proxy_confiavel(
        self, client, token, chat_ok, monkeypatch
    ):
        """Sem proxy confiável declarado, forjar o header não burla o limite por IP."""
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 1)
        assert _chat(client, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
        assert _chat(client, headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429

    def test_valor_forjado_a_esquerda_nao_muda_a_identidade(
        self, client, token, chat_ok, monkeypatch
    ):
        """Proxy que acrescenta: 'forjado, ip-real'. Vale o valor da direita."""
        monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 1)

        assert _chat(client, headers={"X-Forwarded-For": "1.1.1.1, 203.0.113.9"}).status_code == 200
        assert _chat(client, headers={"X-Forwarded-For": "2.2.2.2, 203.0.113.9"}).status_code == 429

    def test_dois_proxies_confiaveis(self, client, token, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 1)

        a = {"X-Forwarded-For": "9.9.9.9, 203.0.113.9, 10.0.0.1"}
        b = {"X-Forwarded-For": "9.9.9.9, 203.0.113.77, 10.0.0.1"}
        assert _chat(client, headers=a).status_code == 200
        assert _chat(client, headers=a).status_code == 429
        assert _chat(client, headers=b).status_code == 200

    def test_header_mais_curto_que_o_esperado_usa_o_ip_da_conexao(
        self, client, token, chat_ok, monkeypatch
    ):
        monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 1)
        assert _chat(client, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
        assert _chat(client, headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429

    def test_limite_zero_desliga_a_contagem(self, client, token, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 0)
        monkeypatch.setattr(settings, "public_rate_limit_global_per_minute", 0)
        assert [_chat(client).status_code for _ in range(30)] == [200] * 30

    def test_texto_longo_demais_e_recusado_para_anonimo(self, client, token, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "public_max_prompt_chars", 50)
        assert _chat(client, prompt="a" * 50).status_code == 200
        resp = _chat(client, prompt="a" * 51)
        assert resp.status_code == 413
        assert chat_ok.complete.call_count == 1

    def test_texto_longo_e_aceito_com_chave(self, client, token, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "public_max_prompt_chars", 50)
        assert _chat(client, prompt="a" * 500, headers=KEY).status_code == 200

    def test_sem_token_nao_ha_limite_nenhum(self, client, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 1)
        monkeypatch.setattr(settings, "public_max_prompt_chars", 10)
        assert [_chat(client, prompt="a" * 100).status_code for _ in range(4)] == [200] * 4


# ═════════════════════════════════════════════════════════════════════════════
# Rotas públicas do portal: TTS
# ═════════════════════════════════════════════════════════════════════════════


class TestTTSPublico:
    def test_chave_errada_devolve_401(self, client, token):
        resp = client.post("/api/audio/tts", json={"text": "olá"}, headers={"X-API-Key": "x"})
        assert resp.status_code == 401

    def test_texto_longo_demais_e_recusado_para_anonimo(self, client, token, monkeypatch):
        monkeypatch.setattr(settings, "public_max_prompt_chars", 20)
        resp = client.post("/api/audio/tts", json={"text": "a" * 21})
        assert resp.status_code == 413

    def test_chat_e_tts_dividem_o_mesmo_limite_por_ip(self, client, token, chat_ok, monkeypatch):
        monkeypatch.setattr(settings, "public_rate_limit_per_minute", 1)
        assert _chat(client).status_code == 200
        assert client.post("/api/audio/tts", json={"text": "olá"}).status_code == 429


# ═════════════════════════════════════════════════════════════════════════════
# SlidingWindowLimiter
# ═════════════════════════════════════════════════════════════════════════════


class TestSlidingWindowLimiter:
    def test_libera_ate_o_limite_e_informa_a_espera(self):
        limiter = SlidingWindowLimiter(window_seconds=60)
        assert limiter.check("a", 2, now=0.0) == 0
        assert limiter.check("a", 2, now=10.0) == 0
        assert limiter.check("a", 2, now=20.0) == pytest.approx(40.0)

    def test_janela_desliza(self):
        limiter = SlidingWindowLimiter(window_seconds=60)
        limiter.check("a", 2, now=0.0)
        limiter.check("a", 2, now=10.0)
        assert limiter.check("a", 2, now=60.5) == 0, "o acesso de t=0 já saiu da janela"
        assert limiter.check("a", 2, now=61.0) > 0

    def test_tentativa_barrada_nao_prolonga_o_bloqueio(self):
        limiter = SlidingWindowLimiter(window_seconds=60)
        limiter.check("a", 1, now=0.0)
        for t in (10.0, 20.0, 30.0, 59.0):
            assert limiter.check("a", 1, now=t) > 0
        assert limiter.check("a", 1, now=60.5) == 0

    def test_chaves_independentes(self):
        limiter = SlidingWindowLimiter()
        assert limiter.check("a", 1, now=0.0) == 0
        assert limiter.check("b", 1, now=0.0) == 0
        assert limiter.check("a", 1, now=1.0) > 0

    def test_limite_zero_ou_negativo_nao_bloqueia(self):
        limiter = SlidingWindowLimiter()
        assert all(limiter.check("a", 0, now=float(i)) == 0 for i in range(50))

    def test_memoria_limitada(self):
        limiter = SlidingWindowLimiter(window_seconds=60, max_keys=100)
        for i in range(1000):
            limiter.check(f"ip:{i}", 5, now=float(i))
        assert len(limiter._hits) <= 101  # 100 chaves + contador de transbordo

    def test_tabela_cheia_nao_zera_contadores_ativos(self):
        """Lotar a tabela com chaves novas não pode liberar quem já estava barrado."""
        limiter = SlidingWindowLimiter(window_seconds=60, max_keys=10)
        assert limiter.check("vitima", 1, now=0.0) == 0
        for i in range(500):
            limiter.check(f"ip:{i}", 1, now=1.0)
        assert limiter.check("vitima", 1, now=2.0) > 0

    def test_chaves_excedentes_dividem_um_contador(self):
        limiter = SlidingWindowLimiter(window_seconds=60, max_keys=3)
        for i in range(3):
            assert limiter.check(f"ip:{i}", 2, now=0.0) == 0
        resultados = [limiter.check(f"novo:{i}", 2, now=1.0) for i in range(5)]
        assert [r == 0 for r in resultados] == [True, True, False, False, False]


class TestPublicLimiter:
    def test_rotatividade_de_ips_nao_zera_o_limite_global(self):
        """10.001 IPs distintos no mesmo minuto: o global segura em 300."""
        from src.core.security import PublicLimiter

        limiter = PublicLimiter()
        admitidas = sum(1 for i in range(10_001) if limiter.check(f"ip:{i}", 20, 300) == 0)
        assert admitidas == 300
