"""Pipelines OpenVINO — Inferência, Áudio e RAG.

Módulo opcional que integra o Intel AI Lab ao monolito FastAPI.
Todos os imports são lazy (dentro dos métodos) para permitir que
o monolito funcione sem OpenVINO instalado.

Pipelines disponíveis:
    - ``OpenVINOPipeline`` — Geração de texto com modelos OpenVINO INT8
    - ``AudioRagPipeline`` — Transcrição Whisper + RAG com FAISS
    - ``is_available()`` — Verifica se OpenVINO + Intel AI Lab estão instalados
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Caminhos padrão ──────────────────────────────────────────

OPENVINO_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent / "AI" / "openvino"
INTEL_AI_LAB_DIR = OPENVINO_PROJECT_DIR / "Intel-AI-Lab"
INTEL_AI_LAB_SRC = INTEL_AI_LAB_DIR / "src"


# ═══════════════════════════════════════════════════════════════
# Utilidades
# ═══════════════════════════════════════════════════════════════


def _ensure_sys_path() -> None:
    """Garante que o src do Intel AI Lab está no sys.path."""
    import sys

    src_str = str(INTEL_AI_LAB_SRC.resolve())
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


# ═══════════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════════


async def is_available() -> bool:
    """Verifica se OpenVINO e dependências Intel AI Lab estão instalados."""
    try:
        # Tenta importar openvino primeiro
        import openvino  # noqa: F401

        # Tenta importar optimum.intel (OVModelForCausalLM)
        from optimum.intel import OVModelForCausalLM  # noqa: F401

        return True
    except ImportError:
        return False
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# Pipeline de Geração de Texto
# ═══════════════════════════════════════════════════════════════


class OpenVINOPipeline:
    """Pipeline de geração de texto com OpenVINO INT8.

    Utiliza modelos do HuggingFace convertidos para OpenVINO IR
    via ``optimum.intel.OVModelForCausalLM``.

    Args:
        model_path: Caminho local ou HF ID do modelo.
        device: Dispositivo de inferência (CPU, GPU, AUTO).
        max_new_tokens: Máximo de tokens a gerar.
        temperature: Temperatura para amostragem.
    """

    def __init__(
        self,
        model_path: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        device: str = "CPU",
        max_new_tokens: int = 256,
        temperature: float = 0.3,
    ) -> None:
        self.model_path = model_path
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self._pipeline = None

    async def _ensure_loaded(self) -> None:
        """Carrega o pipeline (lazy, apenas quando necessário)."""
        if self._pipeline is not None:
            return

        _ensure_sys_path()
        from transformers import AutoTokenizer
        from transformers import pipeline as hf_pipeline

        from optimum.intel import OVModelForCausalLM

        logger.info("Carregando modelo OpenVINO: %s (%s)", self.model_path, self.device)

        is_local = Path(self.model_path).is_dir()
        kwargs: dict[str, Any] = {
            "device": self.device,
            "ov_config": {"PERFORMANCE_HINT": "LATENCY", "NUM_STREAMS": "1"},
        }
        if not is_local:
            kwargs["export"] = True

        model = OVModelForCausalLM.from_pretrained(self.model_path, **kwargs)
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)

        self._pipeline = hf_pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            do_sample=self.temperature > 0,
            pad_token_id=tokenizer.eos_token_id,
        )

        logger.info("Modelo OpenVINO carregado com sucesso")

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Gera texto a partir de um prompt.

        Args:
            prompt: O texto de entrada.
            system_prompt: Instrução de sistema opcional.

        Returns:
            Texto gerado pelo modelo.
        """
        await self._ensure_loaded()
        assert self._pipeline is not None

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        result = self._pipeline(full_prompt)
        generated = result[0]["generated_text"] if isinstance(result, list) else str(result)

        # Remove o prompt da resposta (text-generation retorna prompt+geração)
        if generated.startswith(full_prompt):
            generated = generated[len(full_prompt) :].strip()

        return generated

    async def close(self) -> None:
        """Libera recursos do pipeline."""
        self._pipeline = None
        import gc

        gc.collect()


# ═══════════════════════════════════════════════════════════════
# Pipeline de Áudio + RAG
# ═══════════════════════════════════════════════════════════════


class AudioRagPipeline:
    """Pipeline de áudio com transcrição Whisper + RAG.

    Integra transcrição por Whisper e busca semântica com FAISS
    sobre uma base de conhecimento local.

    Args:
        docs_dir: Diretório com documentos base (txt, md, rst).
        whisper_model: Modelo Whisper a usar.
        device: Dispositivo para inferência (CPU, GPU).
        embedding_model: Modelo de embeddings.
        k: Número de documentos relevantes a retornar.
        cache_dir: Diretório para cache do índice FAISS.
    """

    def __init__(
        self,
        docs_dir: str | None = None,
        whisper_model: str = "openai/whisper-tiny.en",
        device: str = "CPU",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        k: int = 4,
        cache_dir: str | None = None,
    ) -> None:
        self.docs_dir = docs_dir or str(INTEL_AI_LAB_DIR / "docs" / "knowledge-base")
        self.whisper_model = whisper_model
        self.device = device
        self.embedding_model = embedding_model
        self.k = k
        self.cache_dir = cache_dir or str(INTEL_AI_LAB_DIR / "models" / ".rag_cache")
        self._whisper_pipe = None
        self._rag_pipeline = None
        self._vector_count = 0

    async def _ensure_whisper(self):
        """Carrega o pipeline Whisper (lazy)."""
        if self._whisper_pipe is not None:
            return

        from transformers import pipeline

        logger.info("Carregando Whisper: %s", self.whisper_model)
        self._whisper_pipe = pipeline(
            "automatic-speech-recognition",
            model=self.whisper_model,
            chunk_length_s=30,
            return_timestamps=False,
        )

    async def _ensure_rag(self):
        """Carrega os componentes RAG (lazy)."""
        if self._rag_pipeline is not None:
            return

        _ensure_sys_path()

        from langchain_classic.chains import RetrievalQA
        from langchain_community.llms import HuggingFacePipeline
        from langchain_community.vectorstores import FAISS
        from langchain_core.prompts import PromptTemplate
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from optimum.intel import OVModelForCausalLM
        from transformers import AutoTokenizer
        from transformers import pipeline as hf_pipeline

        from langchain_community.document_loaders import TextLoader

        logger.info("Carregando componentes RAG...")

        # Embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # Vector store (FAISS) — tenta cache, senão constrói
        vectorstore = None
        cache_path = Path(self.cache_dir)
        if cache_path.exists() and (cache_path / "index.faiss").exists():
            try:
                vectorstore = FAISS.load_local(
                    str(cache_path), embeddings, allow_dangerous_deserialization=True
                )
                logger.info("Índice FAISS carregado do cache: %s", cache_path)
            except Exception as exc:
                logger.warning("Falha ao carregar cache FAISS: %s", exc)
                vectorstore = None

        if vectorstore is None:
            docs = []
            docs_path = Path(self.docs_dir)
            if docs_path.exists():
                for ext in ["*.txt", "*.md", "*.rst"]:
                    for fpath in sorted(docs_path.rglob(ext)):
                        try:
                            loader = TextLoader(str(fpath), encoding="utf-8")
                            docs.extend(loader.load())
                        except Exception:
                            pass

            if not docs:
                logger.warning("Nenhum documento encontrado em %s", self.docs_dir)
                # Cria índice vazio
                from langchain_community.vectorstores import FAISS

                vectorstore = FAISS.from_texts(["Placeholder"], embeddings)
            else:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", ".", " ", ""]
                )
                chunks = splitter.split_documents(docs)
                vectorstore = FAISS.from_documents(chunks, embeddings)

                cache_path.mkdir(parents=True, exist_ok=True)
                vectorstore.save_local(str(cache_path))
                logger.info(
                    "Índice FAISS criado com %d chunks e salvo em %s", len(chunks), cache_path
                )

        # LLM (OpenVINO)
        local_model = str(INTEL_AI_LAB_DIR / "models" / "openvino" / "tinyllama")
        model_path = (
            local_model if Path(local_model).is_dir() else "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        )

        kwargs: dict[str, Any] = {
            "device": self.device,
            "ov_config": {"PERFORMANCE_HINT": "LATENCY", "NUM_STREAMS": "1"},
        }
        if not Path(model_path).is_dir():
            kwargs["export"] = True

        model = OVModelForCausalLM.from_pretrained(model_path, **kwargs)
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        pipe = hf_pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=256,
            temperature=0.3,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
        llm = HuggingFacePipeline(pipeline=pipe)

        # Cadeia RAG
        retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": self.k})
        template = """Você é um assistente especializado em Intel OpenVINO e IA.
Use o contexto abaixo para responder. Se não souber, diga que não encontrou.

Contexto:
{context}

Pergunta: {question}

Resposta:"""

        prompt = PromptTemplate(template=template, input_variables=["context", "question"])
        self._rag_pipeline = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True,
        )
        self._vector_count = vectorstore.index.ntotal if hasattr(vectorstore, "index") else 0
        logger.info("Pipeline RAG pronto: %d vetores", self._vector_count)

    async def transcribe(self, audio_path: str) -> dict[str, Any]:
        """Transcreve um arquivo de áudio com Whisper.

        Args:
            audio_path: Caminho para o arquivo de áudio.

        Returns:
            Dict com texto transcrito, duração e tempo de transcrição.
        """
        await self._ensure_whisper()
        assert self._whisper_pipe is not None

        import time

        import soundfile as sf

        audio, sr = sf.read(audio_path)
        duration = len(audio) / sr

        t0 = time.perf_counter()
        result = self._whisper_pipe(audio)
        elapsed = time.perf_counter() - t0

        return {
            "text": result["text"].strip(),
            "duration_seconds": duration,
            "transcription_time": elapsed,
            "rtf": elapsed / duration if duration > 0 else 0,
        }

    async def query_rag(self, question: str) -> dict[str, Any]:
        """Faz uma pergunta à base de conhecimento via RAG.

        Args:
            question: Pergunta do usuário.

        Returns:
            Dict com resposta e fontes.
        """
        await self._ensure_rag()
        assert self._rag_pipeline is not None

        import time

        t0 = time.perf_counter()
        result = self._rag_pipeline.invoke({"query": question})
        elapsed = time.perf_counter() - t0

        answer = result.get("result", "")
        sources_raw = result.get("source_documents", [])

        sources = list(
            {
                Path(s.metadata.get("source", "")).name
                for s in (sources_raw or [])[:4]
                if s.metadata.get("source")
            }
        )

        return {
            "answer": answer,
            "sources": sources,
            "latency_ms": round(elapsed * 1000, 1),
            "vector_count": self._vector_count,
        }

    async def close(self) -> None:
        """Libera recursos."""
        self._whisper_pipe = None
        self._rag_pipeline = None
        import gc

        gc.collect()
