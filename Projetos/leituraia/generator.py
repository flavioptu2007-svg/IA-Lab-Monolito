"""Gerador de textos didáticos do LeituraIA Brasil.

Fluxo:
1. Modo IA — chama um endpoint OpenAI-compatível (Z.AI/GLM por padrão neste
   ambiente) com um prompt que exige JSON estruturado. A chave é resolvida
   via ``leituraia.config`` (nunca armazenada em código).
2. Modo template (fallback/offline) — gera um material didático estruturado
   e determinístico (texto + glossário + curiosidades + linha do tempo +
   perguntas + resumo), suficiente para testes, demonstração e uso sem chave.

O conteúdo gerado respeita os metadados pedidos (ano, disciplina, tema,
BNCC/CRMG, nível, objetivo, idioma) — a curadoria curricular real via RAG
(Qdrant) é a evolução planejada, seguindo o padrão do monolito.
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from leituraia import config
from leituraia.models import (
    NIVEL_ROTULO,
    GerarTextoRequest,
    LinhaTempoItem,
    Pergunta,
    TextoGerado,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Você é o LeituraIA Brasil, especialista em produzir materiais de "
    "compreensão leitora para escolas brasileiras, alinhados à BNCC e ao CRMG. "
    "Responda APENAS com JSON válido, sem markdown, com o seguinte formato: "
    '{"titulo": str, "texto": str, "glossario": [str], "curiosidades": [str], '
    '"linha_tempo": [{"data": str, "evento": str}], '
    '"perguntas": [{"pergunta": str, "tipo": "multipla_escolha", "resposta": str}], '
    '"resumo": str, "referencias": [str]}'
)


def _montar_prompt(req: GerarTextoRequest) -> str:
    nivel = NIVEL_ROTULO.get(req.nivel, req.nivel)
    return (
        f"Escreva um texto didático de compreensão leitora em {req.idioma} "
        f"para o {req.ano}º ano, disciplina {req.disciplina}, sobre o tema "
        f"{req.tema!r}.\n"
        f"- Nível: {nivel}\n"
        f"- Objetivo: {req.objetivo}\n"
        f"- Aproximadamente {req.palavras} palavras, parágrafos curtos.\n"
        f"- BNCC: {', '.join(req.bncc) or 'não informada'}\n"
        f"- CRMG: {', '.join(req.crmg) or 'não informado'}\n"
        "O texto deve ser original, correto historicamente/cientificamente e "
        "adequado ao nível. Inclua glossário (3 a 5 termos), curiosidades (2 a 4), "
        "linha do tempo (2 a 5 itens), perguntas de compreensão leitora "
        "(3 a 5, com respostas) e um resumo curto."
    )


def _limpar_json(resposta: str) -> str:
    resposta = resposta.strip()
    resposta = re.sub(r"^```(?:json)?\s*", "", resposta)
    resposta = re.sub(r"\s*```$", "", resposta)
    start = resposta.find("{")
    end = resposta.rfind("}")
    if start >= 0 and end > start:
        return resposta[start : end + 1]
    return resposta


def _chamar_ia(req: GerarTextoRequest) -> dict | None:
    base = config.get_base_url()
    modelo = config.get_model()
    chave = config.get_api_key()
    if not chave or config.is_offline():
        return None
    url = base.rstrip("/") + "/chat/completions"
    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _montar_prompt(req)},
        ],
        "temperature": 0.6,
        "max_tokens": 4096,
    }
    headers = {"Authorization": f"Bearer {chave}", "Content-Type": "application/json"}
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(_limpar_json(content))
    except Exception as exc:  # noqa: BLE001 — fallback deliberado
        logger.warning("Gerador IA falhou (%s); usando template.", exc)
        return None


# ── Template offline ─────────────────────────────────────────────────
def _gerar_template(req: GerarTextoRequest) -> TextoGerado:
    tema = req.tema
    nivel = NIVEL_ROTULO.get(req.nivel, req.nivel)
    palavras_alvo = max(80, req.palavras)

    titulo = f"{tema} — Texto de Compreensão Leitora"
    introducao = (
        f"Vamos conhecer o tema {tema!r}? Neste texto, você vai ler sobre "
        f"este assunto de forma simples e clara. Preste atenção nas "
        f"informações principais: elas vão ajudar você a responder as "
        f"perguntas no final."
    )
    corpo = (
        f"O tema {tema} faz parte dos estudos da disciplina de "
        f"{req.disciplina} no {req.ano}º ano. Para compreender bem este "
        f"assunto, é importante observar três pontos. Primeiro: entender o "
        f"significado das palavras principais, que aparecem no glossário "
        f"deste material. Segundo: identificar as informações centrais, "
        f"como datas, nomes e causas. Terceiro: relacionar o tema com o que "
        f"você já sabe da sua realidade e com o que foi estudado em sala."
    )
    fecho = (
        f"Depois da leitura, pense sobre o que você aprendeu. O objetivo "
        f"desta atividade é {req.objetivo.lower()}. Converse com seu "
        f"professor ou colegas sobre as curiosidades e a linha do tempo "
        f"apresentadas abaixo — isso ajuda a fixar o conteúdo e a melhorar "
        f"sua compreensão leitora."
    )

    # Preenche o texto até o alvo aproximado de palavras, mantendo coesão.
    texto = [introducao, corpo, fecho]
    while sum(len(p.split()) for p in texto) < palavras_alvo:
        texto.insert(
            1,
            f"Um bom leitor lê com atenção, procura o sentido de cada "
            f"parágrafo e faz perguntas sobre o que não entendeu. Ao ler "
            f"sobre {tema}, observe como as informações se organizam e "
            f"como elas se conectam com {req.disciplina} e com o ano "
            f"escolar em que você está.",
        )

    perguntas = [
        Pergunta(
            pergunta="Qual é o tema principal deste texto?",
            tipo="multipla_escolha",
            resposta=f"O tema principal é {tema}.",
        ),
        Pergunta(
            pergunta="Segundo o texto, quais três pontos ajudam a compreender o assunto?",
            tipo="resposta_curta",
            resposta="Entender as palavras principais (glossário), identificar "
            "as informações centrais e relacionar o tema com o que já se sabe.",
        ),
        Pergunta(
            pergunta="Qual é o objetivo da atividade proposta pelo texto?",
            tipo="multipla_escolha",
            resposta=req.objetivo,
        ),
    ]

    return TextoGerado(
        titulo=titulo,
        texto="\n\n".join(texto),
        glossario=[
            "compreensão leitora: habilidade de entender o que se lê.",
            "tema: assunto principal do texto.",
            "glossário: lista de palavras com seus significados.",
        ],
        curiosidades=[
            "Um leitor atento faz perguntas ao próprio texto enquanto lê.",
            "Ler em voz alta ajuda a compreender melhor o que está escrito.",
            f"O tema {tema} pode ser estudado em diferentes disciplinas e anos escolares.",
        ],
        linha_tempo=[
            LinhaTempoItem(data="Antes da leitura", evento="Ativar conhecimentos prévios"),
            LinhaTempoItem(data="Durante a leitura", evento="Identificar informações centrais"),
            LinhaTempoItem(data="Depois da leitura", evento=f"Responder perguntas sobre {tema}"),
        ],
        perguntas=perguntas,
        resumo=(
            f"Este material apresenta o tema {tema} para o {req.ano}º ano "
            f"de {req.disciplina}, em nível {nivel}, com o objetivo de "
            f"desenvolver a compreensão leitora."
        ),
        referencias=[
            "Base Nacional Comum Curricular (BNCC)",
            "Currículo Referência de Minas Gerais (CRMG)",
        ],
        origem="template",
        metadados={
            "ano": req.ano,
            "disciplina": req.disciplina,
            "tema": req.tema,
            "bncc": req.bncc,
            "crmg": req.crmg,
            "nivel": req.nivel,
            "objetivo": req.objetivo,
            "idioma": req.idioma,
            "palavras_contadas": sum(len(p.split()) for p in texto),
            "palavras_pedidas": req.palavras,
        },
    )


def gerar_texto(req: GerarTextoRequest) -> TextoGerado:
    """Gera um material didático; usa IA quando disponível, senão template."""
    dados = _chamar_ia(req) if not config.is_offline() else None
    if dados:
        try:
            return TextoGerado(
                titulo=str(dados.get("titulo", f"{req.tema} — Texto Didático")),
                texto=str(dados.get("texto", "")),
                glossario=list(dados.get("glossario", [])),
                curiosidades=list(dados.get("curiosidades", [])),
                linha_tempo=[
                    LinhaTempoItem(**item)
                    for item in dados.get("linha_tempo", [])
                    if isinstance(item, dict)
                ],
                perguntas=[
                    Pergunta(**p)
                    for p in dados.get("perguntas", [])
                    if isinstance(p, dict) and p.get("pergunta") and p.get("resposta")
                ],
                resumo=str(dados.get("resumo", "")),
                referencias=list(dados.get("referencias", [])),
                origem="ia",
                metadados={
                    "ano": req.ano,
                    "disciplina": req.disciplina,
                    "tema": req.tema,
                    "bncc": req.bncc,
                    "crmg": req.crmg,
                    "nivel": req.nivel,
                    "objetivo": req.objetivo,
                    "idioma": req.idioma,
                    "modelo": config.get_model(),
                },
            )
        except Exception as exc:  # noqa: BLE001 — shape inesperado do LLM
            logger.warning("Resposta da IA fora do formato esperado (%s); template.", exc)
    return _gerar_template(req)


__all__ = ["gerar_texto", "gerar_template" if False else "_gerar_template"]
