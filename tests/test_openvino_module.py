"""Testes do módulo OpenVINO — pipelines, endpoints e health check.

Cobre:
- ``is_available()`` — health check (com/sem OpenVINO)
- ``OpenVINOPipeline`` — geração de texto (com mock do optimum.intel)
- ``AudioRagPipeline`` — transcrição e RAG (com mocks)
- Endpoints FastAPI em ``src/api/v2/openvino.py``
- Router registrado na app principal (api/server.py)

Nota: ``is_available()`` tenta importar openvino + optimum.intel.
      Os testes mockam os imports internos, não a função em si.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ═════════════════════════════════════════════════════════════════════════════
# is_available  —  testa a implementação real mockando os imports internos
# ═════════════════════════════════════════════════════════════════════════════


class TestIsAvailable:
    """Testes para src.openvino.pipelines.is_available().

    A função ``is_available()`` executa ``import openvino`` e
    ``from optimum.intel import OVModelForCausalLM`` dentro de
    um try/except ImportError. Mockamos ``sys.modules`` para
    controlar quais imports estão disponíveis sem precisar
    dos pacotes reais.
    """

    @pytest.mark.asyncio
    async def test_available_quando_openvino_instalado(self):
        """Deve retornar True quando openvino e optimum.intel estão em sys.modules."""
        with patch.dict(
            "sys.modules", {"openvino": MagicMock(), "optimum.intel": MagicMock()}, clear=False
        ):
            from src.openvino.pipelines import is_available

            result = await is_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_unavailable_quando_openvino_ausente(self):
        """Deve retornar False quando openvino não está disponível.

        Força ``is_available()`` a seguir o caminho ``ImportError``
        patcheando o import real dentro do try/except da função.
        """
        # Força o caminho ImportError: is_available tenta import openvino,
        # mas interceptamos o __import__ para simular módulo ausente.
        import builtins

        original_import = builtins.__import__

        def restricted_import(name, *args, **kwargs):
            if name == "openvino":
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=restricted_import):
            from src.openvino.pipelines import is_available

            result = await is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_unavailable_quando_exception_inesperada(self):
        """Deve retornar False quando ocorrer exceção que não seja ImportError."""
        import builtins

        original_import = builtins.__import__

        def broken_import(name, *args, **kwargs):
            if name == "openvino":
                raise RuntimeError("Erro inesperado na importação")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=broken_import):
            from src.openvino.pipelines import is_available

            result = await is_available()
            assert result is False


# ═════════════════════════════════════════════════════════════════════════════
# OpenVINOPipeline
# ═════════════════════════════════════════════════════════════════════════════


class TestOpenVINOPipeline:
    """Testes para OpenVINOPipeline.generate()."""

    @pytest.mark.asyncio
    async def test_generate_retorna_texto(self):
        """Deve gerar texto a partir de um prompt, removendo o prompt da resposta."""
        from src.openvino.pipelines import OpenVINOPipeline

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [{"generated_text": "prompt resposta gerada"}]

        pipe = OpenVINOPipeline()
        pipe._pipeline = mock_pipeline

        result = await pipe.generate("prompt")
        assert result == "resposta gerada"

    @pytest.mark.asyncio
    async def test_generate_com_system_prompt(self):
        """Deve concatenar system_prompt ao prompt e remover o prompt da resposta."""
        from src.openvino.pipelines import OpenVINOPipeline

        pipe = OpenVINOPipeline()
        pipe._pipeline = MagicMock()

        # full_prompt = "sys\n\npergunta" (com newlines reais)
        # A resposta mockada é "sys\n\npergunta resposta"
        pipe._pipeline.return_value = [{"generated_text": "sys\n\npergunta resposta"}]

        result = await pipe.generate("pergunta", system_prompt="sys")
        # generated[len(full_prompt):] = " resposta".strip() = "resposta"
        assert result == "resposta"

    def test_init_com_parametros_personalizados(self):
        """Deve aceitar parâmetros personalizados no construtor."""
        from src.openvino.pipelines import OpenVINOPipeline

        pipe = OpenVINOPipeline(
            model_path="modelo-local", device="GPU", max_new_tokens=512, temperature=0.8
        )
        assert pipe.model_path == "modelo-local"
        assert pipe.device == "GPU"
        assert pipe.max_new_tokens == 512
        assert pipe.temperature == 0.8

    @pytest.mark.asyncio
    async def test_close_libera_recursos(self):
        """O método close deve limpar o pipeline."""
        from src.openvino.pipelines import OpenVINOPipeline

        pipe = OpenVINOPipeline()
        pipe._pipeline = MagicMock()

        await pipe.close()
        assert pipe._pipeline is None


# ═════════════════════════════════════════════════════════════════════════════
# AudioRagPipeline
# ═════════════════════════════════════════════════════════════════════════════


class TestAudioRagPipeline:
    """Testes para AudioRagPipeline — transcrição e RAG."""

    @pytest.mark.asyncio
    async def test_transcribe_retorna_dict_com_texto(self):
        """Deve transcrever áudio e retornar dict com texto."""
        from src.openvino.pipelines import AudioRagPipeline

        pipe = AudioRagPipeline()
        pipe._whisper_pipe = MagicMock()
        pipe._whisper_pipe.return_value = {"text": " transcricao teste "}

        with patch("soundfile.read") as mock_sf_read:
            import numpy as np

            mock_sf_read.return_value = (np.zeros(16000, dtype=np.float32), 16000)

            result = await pipe.transcribe("/fake/audio.wav")
            assert result["text"] == "transcricao teste"
            assert result["duration_seconds"] == 1.0  # 16000 samples / 16000 sr
            assert result["rtf"] > 0

    @pytest.mark.asyncio
    async def test_query_rag_retorna_resposta_e_fontes(self):
        """Deve consultar RAG e retornar resposta com fontes."""
        from src.openvino.pipelines import AudioRagPipeline

        pipe = AudioRagPipeline()
        pipe._rag_pipeline = MagicMock()
        pipe._rag_pipeline.invoke = MagicMock(
            return_value={"result": "Resposta RAG", "source_documents": []}
        )
        pipe._vector_count = 42

        result = await pipe.query_rag("pergunta teste")
        assert result["answer"] == "Resposta RAG"
        assert result["vector_count"] == 42
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_query_rag_extrai_fontes_dos_documentos(self):
        """Deve extrair nomes de fonte dos source_documents."""
        from src.openvino.pipelines import AudioRagPipeline

        mock_doc = MagicMock()
        mock_doc.metadata = {"source": "/path/to/doc.md"}

        pipe = AudioRagPipeline()
        pipe._rag_pipeline = MagicMock()
        pipe._rag_pipeline.invoke = MagicMock(
            return_value={"result": "resposta", "source_documents": [mock_doc]}
        )
        pipe._vector_count = 10

        result = await pipe.query_rag("teste")
        assert "doc.md" in result["sources"]

    def test_init_com_parametros_personalizados(self):
        """Deve aceitar parâmetros personalizados no construtor."""
        from src.openvino.pipelines import AudioRagPipeline

        pipe = AudioRagPipeline(
            docs_dir="/custom/docs",
            whisper_model="openai/whisper-base",
            device="GPU",
            embedding_model="all-MiniLM-L12-v2",
            k=8,
            cache_dir="/custom/cache",
        )
        assert pipe.docs_dir == "/custom/docs"
        assert pipe.whisper_model == "openai/whisper-base"
        assert pipe.device == "GPU"
        assert pipe.embedding_model == "all-MiniLM-L12-v2"
        assert pipe.k == 8
        assert pipe.cache_dir == "/custom/cache"

    @pytest.mark.asyncio
    async def test_close_libera_recursos(self):
        """O método close deve limpar pipelines."""
        from src.openvino.pipelines import AudioRagPipeline

        pipe = AudioRagPipeline()
        pipe._whisper_pipe = MagicMock()
        pipe._rag_pipeline = MagicMock()

        await pipe.close()
        assert pipe._whisper_pipe is None
        assert pipe._rag_pipeline is None


# ═════════════════════════════════════════════════════════════════════════════
# Endpoints FastAPI
# ═════════════════════════════════════════════════════════════════════════════


class TestOpenVINOEndpoints:
    """Testes para os endpoints FastAPI do módulo OpenVINO.

    Usa TestClient da FastAPI para testar as rotas reais.
    Nota: ``is_available`` é importado dentro dos corpos das funções dos
    endpoints. Por isso o patch é em ``src.openvino.pipelines.is_available``
    e não em ``src.api.v2.openvino.is_available``.
    """

    @pytest.fixture
    def client(self):
        """Cria um TestClient com a app principal."""
        from fastapi.testclient import TestClient

        from api.server import app

        return TestClient(app)

    def test_health_endpoint_retorna_200(self, client):
        """GET /api/v2/openvino/health deve retornar 200."""
        response = client.get("/api/v2/openvino/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "openvino_available" in data

    def test_models_endpoint_retorna_200(self, client):
        """GET /api/v2/openvino/models deve retornar 200."""
        response = client.get("/api/v2/openvino/models")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "models" in data
        assert "default" in data

    def test_generate_endpoint_503_quando_openvino_ausente(self, client):
        """POST /api/v2/openvino/generate deve retornar 503 sem OpenVINO."""
        with patch("src.openvino.pipelines.is_available", AsyncMock(return_value=False)):
            response = client.post("/api/v2/openvino/generate", params={"prompt": "teste"})
            assert response.status_code == 503
            assert response.json()["detail"] == "openvino_not_available"

    def test_transcribe_endpoint_503_quando_openvino_ausente(self, client):
        """POST /api/v2/openvino/transcribe deve retornar 503 sem OpenVINO."""
        with patch("src.openvino.pipelines.is_available", AsyncMock(return_value=False)):
            response = client.post(
                "/api/v2/openvino/transcribe",
                files={"audio": ("test.wav", b"fakeaudio", "audio/wav")},
            )
            assert response.status_code == 503
            assert response.json()["detail"] == "openvino_not_available"

    def test_rag_query_endpoint_503_quando_openvino_ausente(self, client):
        """POST /api/v2/openvino/rag/query deve retornar 503 sem OpenVINO."""
        with patch("src.openvino.pipelines.is_available", AsyncMock(return_value=False)):
            response = client.post("/api/v2/openvino/rag/query", params={"question": "teste"})
            assert response.status_code == 503
            assert response.json()["detail"] == "openvino_not_available"

    def test_health_router_registrado_na_app(self, client):
        """O router openvino deve estar registrado na app principal.

        Em FastAPI >=0.100, ``include_router()`` adiciona objetos
        ``_IncludedRouter`` que encapsulam as rotas do APIRouter.
        Extraímos os paths percorrendo recursivamente.
        """
        from api.server import app

        def _extrair_paths(route_obj):
            """Extrai paths recursivamente de APIRoute e _IncludedRouter.

            Em FastAPI >=0.100, ``include_router()`` cria objetos
            ``_IncludedRouter`` com o atributo ``original_router``
            (não ``router``) contendo o APIRouter original.
            """
            paths = []
            if hasattr(route_obj, "path"):
                paths.append(route_obj.path)
            # Tenta original_router (FastAPI >=0.100) e router fallback
            for router_attr in ("original_router", "router"):
                router = getattr(route_obj, router_attr, None)
                if router and hasattr(router, "routes"):
                    for sub in router.routes:
                        if hasattr(sub, "path"):
                            paths.append(sub.path)
                    break
            return paths

        all_paths = []
        for r in app.routes:
            all_paths.extend(_extrair_paths(r))

        assert "/api/v2/openvino/health" in all_paths, (
            f"Rota não encontrada. Paths disponíveis: {all_paths}"
        )
        assert "/api/v2/openvino/generate" in all_paths
        assert "/api/v2/openvino/transcribe" in all_paths
        assert "/api/v2/openvino/rag/query" in all_paths
        assert "/api/v2/openvino/models" in all_paths


# ═════════════════════════════════════════════════════════════════════════════
# Endpoints — Testes de Sucesso (HTTP 200)
# ═════════════════════════════════════════════════════════════════════════════


class TestOpenVINOEndpointsSucesso:
    """Testes de sucesso para endpoints OpenVINO.

    Mocka ``is_available()=True`` + as pipelines para simular
    OpenVINO instalado sem precisar dos pacotes reais.

    Nota: ``is_available``, ``OpenVINOPipeline`` e ``AudioRagPipeline``
    são importados DENTRO dos corpos das funções dos endpoints.
    Por isso os patches são nos paths de origem ``src.openvino.pipelines.*``
    e não ``src.api.v2.openvino.*``.
    """

    @pytest.fixture
    def client(self):
        """Cria um TestClient com a app principal."""
        from fastapi.testclient import TestClient

        from api.server import app

        return TestClient(app)

    @pytest.fixture
    def mock_openvino_instalado(self):
        """Mocka is_available()=True para todos os testes da classe."""
        with patch("src.openvino.pipelines.is_available", AsyncMock(return_value=True)):
            yield

    # ── Generate ──────────────────────────────────────────────────

    def _make_mock_pipeline(self, **mock_methods):
        """Cria um mock de pipeline com close() async.

        O método ``close()`` é chamado no ``finally`` dos endpoints
        via ``await pipe.close()``, então precisa ser AsyncMock.
        """
        pipe = MagicMock()
        for name, mock_obj in mock_methods.items():
            setattr(pipe, name, mock_obj)
        # close() é chamado via await no finally — obrigatório AsyncMock
        pipe.close = AsyncMock()
        return pipe

    def test_generate_retorna_200_com_output(self, client, mock_openvino_instalado):
        """POST /api/v2/openvino/generate deve retornar 200 com output."""
        mock_pipeline = self._make_mock_pipeline(
            generate=AsyncMock(return_value="resposta simulada do OpenVINO")
        )

        with patch("src.openvino.pipelines.OpenVINOPipeline", return_value=mock_pipeline):
            response = client.post(
                "/api/v2/openvino/generate", params={"prompt": "explique IA", "max_new_tokens": 100}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["output"] == "resposta simulada do OpenVINO"
        assert "model" in data
        assert "device" in data

    def test_generate_chama_close_ao_final(self, client, mock_openvino_instalado):
        """O método close() deve ser chamado no finally do endpoint."""
        mock_pipeline = self._make_mock_pipeline(generate=AsyncMock(return_value="ok"))

        with patch("src.openvino.pipelines.OpenVINOPipeline", return_value=mock_pipeline):
            client.post("/api/v2/openvino/generate", params={"prompt": "teste"})

        # close() é chamado no finally do endpoint
        mock_pipeline.close.assert_awaited_once()

    def test_generate_com_system_prompt(self, client, mock_openvino_instalado):
        """POST deve aceitar system_prompt opcional."""
        mock_pipeline = self._make_mock_pipeline(generate=AsyncMock(return_value="resposta"))

        with patch("src.openvino.pipelines.OpenVINOPipeline", return_value=mock_pipeline):
            response = client.post(
                "/api/v2/openvino/generate",
                params={"prompt": "pergunta", "system_prompt": "seja conciso", "temperature": 0.5},
            )

        assert response.status_code == 200
        assert response.json()["output"] == "resposta"

    # ── Transcribe ───────────────────────────────────────────────

    def test_transcribe_retorna_200_com_texto(self, client, mock_openvino_instalado):
        """POST /api/v2/openvino/transcribe deve retornar 200 com transcrição."""
        import tempfile

        # Cria um arquivo WAV mínimo válido para upload
        # Gera bytes WAV válidos sem dependência do soundfile
        import wave
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name

        try:
            # Cria um WAV PCM 16-bit mono 16kHz válido com 0.5s de silêncio
            sample_rate = 16000
            num_samples = 8000
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(b"\x00\x00" * num_samples)

            with open(wav_path, "rb") as f:
                audio_bytes = f.read()

            mock_pipeline = self._make_mock_pipeline(
                transcribe=AsyncMock(
                    return_value={
                        "text": "audio transcrito",
                        "duration_seconds": 0.5,
                        "transcription_time": 0.3,
                        "rtf": 0.6,
                    }
                )
            )

            with patch("src.openvino.pipelines.AudioRagPipeline", return_value=mock_pipeline):
                response = client.post(
                    "/api/v2/openvino/transcribe",
                    files={"audio": ("test.wav", audio_bytes, "audio/wav")},
                    params={"whisper_model": "openai/whisper-tiny.en"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["text"] == "audio transcrito"
            assert data["duration_seconds"] == 0.5
            assert "rtf" in data
        finally:
            Path(wav_path).unlink(missing_ok=True)

    # ── RAG Query ────────────────────────────────────────────────

    def test_rag_query_retorna_200_com_resposta(self, client, mock_openvino_instalado):
        """POST /api/v2/openvino/rag/query deve retornar 200 com resposta."""
        mock_pipeline = self._make_mock_pipeline(
            query_rag=AsyncMock(
                return_value={
                    "answer": "Resposta baseada nos documentos",
                    "sources": ["doc1.md", "doc2.md"],
                    "latency_ms": 150.0,
                    "vector_count": 42,
                }
            )
        )

        with patch("src.openvino.pipelines.AudioRagPipeline", return_value=mock_pipeline):
            response = client.post(
                "/api/v2/openvino/rag/query", params={"question": "o que é OpenVINO?", "k": 3}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["answer"] == "Resposta baseada nos documentos"
        assert len(data["sources"]) == 2
        assert data["vector_count"] == 42
        assert data["latency_ms"] > 0

    def test_rag_query_com_docs_dir_personalizado(self, client, mock_openvino_instalado):
        """POST deve aceitar docs_dir personalizado."""
        mock_pipeline = self._make_mock_pipeline(
            query_rag=AsyncMock(
                return_value={
                    "answer": "resposta",
                    "sources": [],
                    "latency_ms": 100.0,
                    "vector_count": 10,
                }
            )
        )

        with patch("src.openvino.pipelines.AudioRagPipeline", return_value=mock_pipeline):
            response = client.post(
                "/api/v2/openvino/rag/query",
                params={"question": "teste", "docs_dir": "/custom/path"},
            )

        assert response.status_code == 200
        mock_pipeline.query_rag.assert_awaited_once()


# ═════════════════════════════════════════════════════════════════════════════
# Módulo __init__.py
# ═════════════════════════════════════════════════════════════════════════════


class TestOpenVINOModule:
    """Testes para o pacote src.openvino."""

    def test_version_exportada(self):
        """O módulo deve exportar __version__."""
        import src.openvino

        assert hasattr(src.openvino, "__version__")
