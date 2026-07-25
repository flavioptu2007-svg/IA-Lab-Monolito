"""Classificador inteligente de tarefas.

Analisa o prompt do usuário e determina o tipo de tarefa
para rotear para o provedor de IA mais adequado.
"""

from __future__ import annotations

import re
from ai.providers.base import TaskType


class TaskClassifier:
    """Classifica prompts em tipos de tarefa baseado em heurísticas."""

    # Padrões para cada tipo de tarefa
    PATTERNS: dict[TaskType, list[str]] = {
        TaskType.code: [
            r"\b(código|code|função|funcao|implementar|programar|bug|refatorar|api|endpoint|teste unitário|classe|método)\b",
            r"\b(python|javascript|typescript|java|rust|go|react|fastapi|flask|sql)\b",
            r"\b(escreva|faça|crie|desenvolva|corrija|implemente) .* (função|código|classe|script)\b",
        ],
        TaskType.refactor: [
            r"\b(refatorar|refatoração|refatoracao|melhorar|otimizar|simplificar|clean code|revisar)\b",
            r"\b(duplicated|repetido|complexidade|manutenção|manutencao|legado)\b",
        ],
        TaskType.architecture: [
            r"\b(arquitetura|architecture|design pattern|diagrama|fluxo|infra|estrutura|escalabilidade)\b",
            r"\b(microsserviço|monolito|evento|mensageria|banco de dados|fila|cache)\b",
        ],
        TaskType.planning: [
            r"\b(planejar|planejamento|plano|roadmap|sprint|tarefa|organizar|estratégia)\b",
            r"\b(próximos? passos?|prioridade|prazo|etapa|fase|milestone)\b",
        ],
        TaskType.analysis: [
            r"\b(analisar|análise|analise|investigar|diagnóstico|diagnostico|depurar|debug)\b",
            r"\b(por que|qual a causa|root cause|logs?|erro|exception|traceback)\b",
        ],
        TaskType.creative: [
            r"\b(escreva|crie|gere) (um texto|um poema|uma história|uma estória|um roteiro)\b",
            r"\b(criativo|copywriting|redação|redacao|conteúdo|conteudo|marketing)\b",
        ],
        TaskType.rag: [
            r"\b(pesquisar|buscar|encontrar informação|documento|documentação|knowledge|base de conhecimento)\b",
            r"\b(resumir|sumarizar|extrair|o que diz|o que é |explique o que)\b.*\b(documento|artigo|texto|arquivo)\b",
        ],
    }

    # Palavras-chave fortes que sobrescrevem outras classificações
    OVERRIDE_KEYWORDS: dict[str, TaskType] = {
        "código": TaskType.code,
        "codigo": TaskType.code,
        "programar": TaskType.code,
        "refatorar": TaskType.refactor,
        "arquitetura": TaskType.architecture,
        "planejar": TaskType.planning,
    }

    @classmethod
    def classify(cls, prompt: str) -> TaskType:
        """Classifica o prompt em um tipo de tarefa.

        Args:
            prompt: O texto do prompt do usuário.

        Returns:
            O tipo de tarefa mais provável.
        """
        text = prompt.lower().strip()

        if not text:
            return TaskType.general

        # Verifica palavras-chave de override primeiro
        for keyword, task_type in cls.OVERRIDE_KEYWORDS.items():
            if keyword in text:
                return task_type

        # Pontua cada categoria
        scores: dict[TaskType, int] = {}
        for task_type, patterns in cls.PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                score += len(matches)
            if score > 0:
                scores[task_type] = score

        if not scores:
            return TaskType.general

        # Retorna o tipo com maior pontuação
        return max(scores, key=scores.get)
