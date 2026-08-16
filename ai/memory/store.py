"""VectorStore para RAG usando Qdrant."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai.settings import settings

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class VectorStore:
    """Interface para o banco vetorial Qdrant.

    Fornece métodos singleton com lazy-init e close() explícito
    para liberar conexões no shutdown da aplicação.
    """

    _instance: VectorStore | None = None
    _client: QdrantClient | None = None

    def __new__(cls) -> VectorStore:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self.host = settings.qdrant_host
        self.port = settings.qdrant_port
        self.collection = settings.qdrant_collection
        self._client = None
        self._initialized = True

    def _get_client(self):
        """Retorna o cliente Qdrant (cria sob demanda)."""
        from qdrant_client import QdrantClient

        if self._client is None:
            self._client = QdrantClient(host=self.host, port=self.port, timeout=5.0)
        return self._client

    def is_available(self) -> bool:
        """Verifica se o servidor Qdrant está acessível."""
        try:
            client = self._get_client()
            client.get_collections()
            return True
        except Exception:
            return False

    async def search(self, query: str, limit: int = 5, score_threshold: float = 0.6) -> list[dict]:
        """Busca documentos similares no Qdrant."""
        if not settings.rag_enabled:
            return []

        try:
            client = self._get_client()

            results = client.query(
                collection_name=self.collection,
                query_text=query,
                limit=limit,
                score_threshold=score_threshold,
            )

            documents = []
            for point in results:
                documents.append(
                    {
                        "id": point.id,
                        "score": point.score,
                        "text": point.payload.get("text", "") if point.payload else "",
                        "metadata": (
                            {k: v for k, v in point.payload.items() if k != "text"}
                            if point.payload
                            else {}
                        ),
                    }
                )
            return documents
        except Exception:
            return []

    async def add_document(self, doc_id: str, text: str, metadata: dict | None = None) -> bool:
        """Adiciona um documento ao Qdrant."""
        try:
            client = self._get_client()

            payload = {"text": text}
            if metadata:
                payload.update(metadata)

            client.upsert(
                collection_name=self.collection, points=[{"id": doc_id, "payload": payload}]
            )
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Fecha a conexão com Qdrant.

        Deve ser chamado no shutdown da aplicação para liberar
        o socket HTTP do cliente gRPC/REST.
        """
        if self._client is not None:
            try:
                self._client.close()
                logger.info("VectorStore: conexão Qdrant fechada")
            except Exception as exc:
                logger.warning("VectorStore: erro ao fechar Qdrant: %s", exc)
            finally:
                self._client = None
