"""Esquemas Pydantic — o contrato entre a sessão de redação e o pipeline.

Regra inviolável: o código de habilidade nunca é texto livre — entra como o
objeto ``HabilidadeCatalogo`` inteiro, resultado da consulta ao catálogo, com
a confirmação do professor registrada. Na montagem, os textos vêm sempre da
cópia canônica do catálogo (o objeto embutido identifica; o catálogo fornece).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Modo = Literal["regular", "adaptado"]
ORIGEM = Literal["web", "livro", "documento_apoio"]
TIPO_FONTE = Literal["primaria", "secundaria", "ilustracao"]
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

LACUNA = "___"


def _unicos(valores: list[str], campo: str) -> list[str]:
    """Textos sem vazio e sem repetição (sem distinguir maiúsculas)."""
    limpos = [" ".join(valor.split()) for valor in valores]
    if any(not valor for valor in limpos):
        raise ValueError(f"{campo} não pode ter item vazio")
    caixas = [valor.casefold() for valor in limpos]
    repetidos = {valor for valor in caixas if caixas.count(valor) > 1}
    if repetidos:
        raise ValueError(f"{campo} com repetição: {sorted(repetidos)}")
    return limpos


class FonteRef(BaseModel):
    """Referência estruturada de uma fonte citada — obrigatória por fato."""

    tipo: TIPO_FONTE
    origem: ORIGEM
    obra: str = Field(min_length=1, description="Obra/título/página ou documento consultado")
    autor: str = ""
    ano: str = ""
    url: str | None = Field(default=None, description="Obrigatória quando origem == 'web'")
    data_acesso: str = Field(description="AAAA-MM-DD")

    @field_validator("data_acesso")
    @classmethod
    def _data_valida(cls, v: str) -> str:
        if not _DATA.match(v):
            raise ValueError("data_acesso deve ser AAAA-MM-DD")
        return v

    @model_validator(mode="after")
    def _url_obrigatoria_na_web(self) -> "FonteRef":
        if self.origem == "web" and not self.url:
            raise ValueError("fonte de origem 'web' exige url da página original")
        return self


class BlocoLeitura(BaseModel):
    """Bloco de leitura com fonte; no modo adaptado, pergunta imediatamente após."""

    texto: str = Field(min_length=1)
    pergunta: str = ""
    fonte: FonteRef


class ItemCompletar(BaseModel):
    """Frase com lacuna (``___``), resposta e distratores do banco de palavras."""

    frase_com_lacuna: str = Field(min_length=1)
    resposta: str = Field(min_length=1)
    distratores: list[str] = Field(default_factory=list)
    fonte: FonteRef

    @field_validator("frase_com_lacuna")
    @classmethod
    def _tem_lacuna(cls, v: str) -> str:
        if LACUNA not in v:
            raise ValueError(f"frase_com_lacuna deve conter '{LACUNA}'")
        return v


class ParLigar(BaseModel):
    """Par da atividade de ligar (personagem/evento/local ↔ descrição)."""

    esquerda: str = Field(min_length=1)
    direita: str = Field(min_length=1)
    fonte: FonteRef


class ItemMarcar(BaseModel):
    """Item de marcar/circular/pintar: a resposta é escolhida, não escrita.

    É a forma de menor exigência motora — a folha imprime as opções com um espaço
    de marcação ``( )`` na frente de cada uma.
    """

    enunciado: str = Field(
        min_length=1, description="Comando do item, ex. 'Pinte a palavra certa.'"
    )
    frase: str = Field(default="", description="Frase de apoio, quando o item não basta")
    opcoes: list[str] = Field(min_length=2, max_length=4)
    correta: str = Field(min_length=1)
    fonte: FonteRef

    @field_validator("opcoes")
    @classmethod
    def _opcoes_unicas(cls, v: list[str]) -> list[str]:
        normalizadas = [opcao.strip() for opcao in v]
        if any(not opcao for opcao in normalizadas):
            raise ValueError("opcoes não pode ter item vazio")
        caixas = [opcao.casefold() for opcao in normalizadas]
        repetidas = {opcao for opcao in caixas if caixas.count(opcao) > 1}
        if repetidas:
            raise ValueError(f"opcoes com repetição: {sorted(repetidas)}")
        return normalizadas

    @model_validator(mode="after")
    def _correta_entre_as_opcoes(self) -> "ItemMarcar":
        if self.correta.strip().casefold() not in [opcao.casefold() for opcao in self.opcoes]:
            raise ValueError(f"correta {self.correta!r} não está entre as opções")
        return self


class ItemVerdadeiroFalso(BaseModel):
    """Afirmação com marcação Verdadeiro/Falso — uma decisão por item, sem escrita."""

    afirmacao: str = Field(min_length=1)
    verdadeiro: bool
    correcao: str = Field(
        default="", description="O que é correto; obrigatório quando a afirmação é falsa"
    )
    fonte: FonteRef

    @model_validator(mode="after")
    def _falsa_explica_no_gabarito(self) -> "ItemVerdadeiroFalso":
        if not self.verdadeiro and not self.correcao.strip():
            raise ValueError(
                "afirmação falsa exige 'correcao' — o gabarito mostra o que é correto, "
                "senão o estudante fica sem a informação certa"
            )
        return self


class ItemParearIguais(BaseModel):
    """Parear iguais — a mesma palavra nas duas colunas, em ordens diferentes.

    É o item de menor exigência motora depois do marcar: a resposta é um traço
    entre duas palavras idênticas, sem escrita e sem leitura nova.
    """

    palavras: list[str] = Field(min_length=2, max_length=6)
    fonte: FonteRef

    @field_validator("palavras")
    @classmethod
    def _palavras_unicas(cls, v: list[str]) -> list[str]:
        return _unicos(v, "palavras")


class ItemOrdenar(BaseModel):
    """Ordenação — ``itens`` entra na ordem correta e sai embaralhado na folha.

    A ordem correta é a da lista: é dela que sai o gabarito.
    """

    enunciado: str = Field(min_length=1)
    itens: list[str] = Field(min_length=2, max_length=6)
    fonte: FonteRef

    @field_validator("itens")
    @classmethod
    def _itens_unicos(cls, v: list[str]) -> list[str]:
        return _unicos(v, "itens")


class Figura(BaseModel):
    """Figura de apoio (arquivo local) para apontar ou circular.

    O caminho é conferido na validação de entrada — sem a imagem não há folha:
    o pipeline nunca desenha um substituto no lugar de um arquivo ausente.
    """

    caminho: str = Field(min_length=1, description="PNG ou JPEG, absoluto ou relativo à entrada")
    legenda: str = ""
    fonte: FonteRef


class HabilidadeCatalogo(BaseModel):
    """Habilidade literal do catálogo — o código nunca é texto livre."""

    codigo: str = Field(min_length=1)
    descricao: str = Field(min_length=1)
    ano: str = Field(min_length=1)
    unidade_tematica: str = ""
    objeto_conhecimento: str = ""
    pagina: int = Field(ge=1)
    tipo_modificacao: str = "original"


class MetaCatalogo(BaseModel):
    """Metadados de proveniência do catálogo fechado."""

    documento: str
    url_oficial: str
    url_pdf: str
    versao: str
    data_acesso: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    pdf_md5: str = Field(pattern=r"^[0-9a-f]{32}$")
    pdf_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    escopo: str = ""
    contagens_esperadas: dict[str, int] = Field(default_factory=dict)
    legenda_modificacoes: dict[str, str] = Field(default_factory=dict)
    revisao_aprovada: bool = False
    revisado_por: str | None = None
    revisao_metodo: str = ""
    revisao_data: str = ""
    extraido_em: str = ""
    ferramenta: str = ""
    anomalias_do_documento: list[str] = Field(default_factory=list)


class RespostaProfessor(BaseModel):
    """Registro de uma pergunta do CUJ 4 e da resposta do professor."""

    pergunta: str = Field(min_length=1)
    resposta: str = Field(min_length=1)


class Reprovacao(BaseModel):
    """Item reprovado na validação — a folha só é gerada com a lista vazia."""

    campo: str
    motivo: str

    def __str__(self) -> str:  # noqa: D105 — mensagem direta para o professor
        return f"[{self.campo}] {self.motivo}"


class Planejamento(BaseModel):
    """Ficha de planejamento do professor (GAP-2 residual da Fase 4).

    O caderno de referência adaptado à mão abre com objetivo, duração,
    metodologia, recursos e público/PDI; a página do professor imprimia o
    registro da mediação e o "como aplicar", mas não essa ficha. Todos os
    campos são opcionais — só o que o professor preencher é impresso.
    """

    objetivo: str = ""
    duracao: str = ""
    metodologia: str = ""
    recursos: list[str] = Field(default_factory=list)
    publico: str = Field(default="", description="Público/PDI — sem laudos ou diagnósticos")

    @field_validator("recursos")
    def _recursos_sem_vazio(cls, v: list[str]) -> list[str]:
        return [recurso.strip() for recurso in v if recurso.strip()]

    @model_validator(mode="after")
    def _tem_conteudo(self) -> "Planejamento":
        if not (
            self.objetivo.strip()
            or self.duracao.strip()
            or self.metodologia.strip()
            or self.recursos
            or self.publico.strip()
        ):
            raise ValueError("planejamento sem nenhum campo preenchido")
        return self


class AtividadeEntrada(BaseModel):
    """``atividade.json`` — entrada única do pipeline de montagem."""

    tema: str = Field(min_length=1)
    ano: str = Field(min_length=1)
    modo: Modo
    nivel_suporte: int = Field(default=2, ge=1, le=3)
    habilidade: HabilidadeCatalogo
    confirmado_pelo_professor: bool
    blocos: list[BlocoLeitura] = Field(default_factory=list)
    figuras: list[Figura] = Field(default_factory=list)
    itens_parear: list[ItemParearIguais] = Field(default_factory=list)
    itens_marcar: list[ItemMarcar] = Field(default_factory=list)
    itens_vf: list[ItemVerdadeiroFalso] = Field(default_factory=list)
    itens_ordenar: list[ItemOrdenar] = Field(default_factory=list)
    itens_completar: list[ItemCompletar] = Field(default_factory=list)
    pares_ligar: list[ParLigar] = Field(default_factory=list)
    vocabulario: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="Palavras-chave da folha, impressas na caixa de vocabulário do topo",
    )
    quantidade_questoes: int | None = Field(default=None, ge=1)
    gabarito: bool = False
    registro_mediacao: bool = Field(
        default=False, description="Página final de uso do professor (registro + como aplicar)"
    )
    orientacoes_aplicacao: list[str] = Field(
        default_factory=list,
        description="Orientações do professor, impressas na página de registro",
    )
    planejamento: Planejamento | None = Field(
        default=None,
        description="Ficha de planejamento impressa na página do professor (exige registro_mediacao)",
    )
    observacoes_pedagogicas: str = ""
    documento_apoio: str = ""
    respostas_do_professor: list[RespostaProfessor] = Field(default_factory=list)

    @field_validator("vocabulario")
    @classmethod
    def _vocabulario_unico(cls, v: list[str]) -> list[str]:
        return _unicos(v, "vocabulario")

    @property
    def total_questoes(self) -> int:
        return (
            len([b for b in self.blocos if b.pergunta])
            + len(self.itens_parear)
            + len(self.itens_marcar)
            + len(self.itens_vf)
            + len(self.itens_ordenar)
            + len(self.itens_completar)
            + len(self.pares_ligar)
        )

    @model_validator(mode="after")
    def _tem_questoes(self) -> "AtividadeEntrada":
        if self.total_questoes < 1:
            raise ValueError(
                "a atividade precisa de ao menos uma pergunta, item de parear ou de marcar, "
                "afirmação V/F, item de ordenar ou de completar, ou par de ligar"
            )
        if self.quantidade_questoes is not None and self.quantidade_questoes != self.total_questoes:
            raise ValueError(
                f"quantidade_questoes={self.quantidade_questoes} diverge do total de questões "
                f"preenchidas ({self.total_questoes})"
            )
        return self
