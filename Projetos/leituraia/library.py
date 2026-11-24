"""Biblioteca do LeituraIA Brasil — acervo de textos didáticos.

Acervo e leituras persistidos via SQLAlchemy ORM (tabelas ``textos``/``leituras``).
O acervo inicial é semeado apenas quando a tabela está vazia, com materiais
produzidos no ecossistema do professor (Feudalismo, fontes do Project Gutenberg)
— demonstração de curadoria multi-disciplinar.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from leituraia import db, orm
from leituraia.models import Pergunta, TextoCreate, TextoOut

# ── Textos semeados ──────────────────────────────────────────────────
_SEED: list[dict[str, Any]] = [
    {
        "titulo": "O que é o feudalismo?",
        "conteudo": (
            "O feudalismo foi um sistema de organização da sociedade e da "
            "economia que se desenvolveu na Europa durante a Idade Média, "
            "entre os séculos V e XV. Ele surgiu depois da queda do Império "
            "Romano, em um período de muitas guerras e invasões. Como a vida "
            "era muito perigosa, as pessoas procuravam a proteção de homens "
            "poderosos que possuíam terras.\n\n"
            "A terra, chamada de feudo, era a maior riqueza da época. Quem "
            "tinha terra tinha poder. A sociedade feudal era dividida em três "
            "grupos: o clero, que rezava; a nobreza, que lutava; e os "
            "camponeses, também chamados de servos, que trabalhavam na terra "
            "e produziam os alimentos de todos. Dizia-se que 'uns rezam, "
            "outros lutam, outros trabalham'.\n\n"
            "No feudo, quase tudo o que as pessoas precisavam — comida, roupa "
            "e moradia — era produzido dentro da própria propriedade. Por "
            "isso, o comércio entre as regiões era muito pequeno. O servo "
            "não era escravo: ele não podia ser vendido, mas também não "
            "podia sair do feudo sem a permissão do senhor."
        ),
        "autor": "LeituraIA Brasil (material didático)",
        "ano": "7",
        "disciplina": "História",
        "tema": "Feudalismo",
        "nivel": "fundamental2",
        "tipo": "expositivo",
        "genero": "artigo didático",
        "idioma": "pt-BR",
        "tags": ["medieval", "sociedade", "feudalismo", "BNCC"],
        "bncc": [],
        "crmg": [],
        "glossario": [
            "feudo: grande propriedade de terra que pertencia a um senhor feudal.",
            "servo: camponês que trabalhava no feudo com muitas obrigações para o senhor.",
            "clero: grupo formado por padres, bispos e monges, que rezava e cuidava da religião.",
        ],
        "perguntas": [
            Pergunta(
                pergunta="Quando o feudalismo se desenvolveu na Europa?",
                tipo="multipla_escolha",
                resposta="Durante a Idade Média, entre os séculos V e XV.",
            ),
            Pergunta(
                pergunta="Quais eram os três grupos da sociedade feudal?",
                tipo="multipla_escolha",
                resposta="Clero (rezava), nobreza (lutava) e camponeses (trabalhavam).",
            ),
            Pergunta(
                pergunta="Por que o comércio entre as regiões era muito pequeno?",
                tipo="resposta_curta",
                resposta="Porque quase tudo o que as pessoas precisavam era produzido dentro do próprio feudo.",
            ),
            Pergunta(
                pergunta="O servo era escravo? Explique com base no texto.",
                tipo="dissertativa",
                resposta="Não. O servo não podia ser vendido, mas também não podia sair do feudo sem permissão do senhor.",
            ),
        ],
    },
    {
        "titulo": "Caminha e o primeiro contato com os indígenas (1500)",
        "conteudo": (
            "O primeiro e grande historiador que o Brasil teve, ainda hoje o "
            "mais sincero e verídico, é Pero Vaz de Caminha, o modesto "
            "escrivão que narrou ao rei D. Manuel, numa comovente e "
            "encantadora carta, a história da travessia, da chegada e da "
            "permanência de Cabral na terra brasileira. A carta foi escrita "
            "de Porto Seguro e datada de 1º de maio de 1500.\n\n"
            "Descrevendo o que fizeram os indígenas que acudiram à praia, "
            "Caminha diz que 'os índios logo trouxeram cabaças e, tomando "
            "alguns barris que nós levávamos, enchiam-nos de água e traziam-"
            "nos aos batéis'. Quando a tripulação beijou a cruz erguida na "
            "praia, os indígenas também a beijaram, pondo-se de joelhos — "
            "gestos que levaram Caminha a afirmar que eram 'gente de tal "
            "inocência que, se os entendêssemos e eles a nós, seriam logo "
            "cristãos, porque, segundo parece, não têm nenhuma crença'.\n\n"
            "Caminha ainda escreveu que 'esta gente é boa, e imprimir-se-á "
            "ligeiramente neles qualquer cunho que lhe quiserem dar'. Essa "
            "frase mostra o olhar dos portugueses: eles viam os povos "
            "originários como uma 'folha em branco', pronta para receber a "
            "fé cristã e os costumes europeus. Hoje, estudar essa carta é "
            "estudar uma fonte histórica preciosa — e também refletir sobre "
            "como os europeus enxergavam (e muitas vezes desrespeitavam) os "
            "povos que já viviam aqui."
        ),
        "autor": "LeituraIA Brasil — a partir da Carta de Pero Vaz de Caminha (domínio público)",
        "ano": "7",
        "disciplina": "História",
        "tema": "Descobrimento do Brasil",
        "nivel": "fundamental2",
        "tipo": "expositivo",
        "genero": "fonte histórica comentada",
        "idioma": "pt-BR",
        "tags": ["fontes", "caminha", "descobrimento", "indigenas"],
        "bncc": ["EF07HI04"],
        "crmg": [],
        "glossario": [
            "escrivão: funcionário que escrevia e registrava documentos oficiais.",
            "fonte histórica: documento ou objeto que traz informações sobre o passado.",
            "cunho: marca feita em uma moeda; no texto, a ideia de 'moldar' as pessoas.",
        ],
        "perguntas": [
            Pergunta(
                pergunta="Quem escreveu a carta de 1º de maio de 1500?",
                tipo="multipla_escolha",
                resposta="Pero Vaz de Caminha, escrivão da frota de Cabral.",
            ),
            Pergunta(
                pergunta="O que os indígenas fizeram quando chegaram à praia?",
                tipo="resposta_curta",
                resposta="Trouxeram cabaças, encheram os barris de água e os levaram aos batéis.",
            ),
            Pergunta(
                pergunta="O que a frase 'qualquer cunho que lhe quiserem dar' revela sobre o olhar europeu?",
                tipo="dissertativa",
                resposta="Revela que os europeus viam os indígenas como uma folha em branco, pronta para receber a fé e os costumes europeus.",
            ),
            Pergunta(
                pergunta="Por que a carta de Caminha é considerada uma fonte histórica importante?",
                tipo="dissertativa",
                resposta="Porque é um relato de testemunha ocular, escrito na época, que descreve o primeiro contato dos portugueses com os indígenas.",
            ),
        ],
    },
    {
        "titulo": "O ciclo da água na natureza",
        "conteudo": (
            "A água está sempre em movimento na natureza. Ela muda de lugar "
            "e de estado físico — líquido, sólido e gasoso — em um processo "
            "contínuo chamado ciclo da água.\n\n"
            "O sol aquece a água dos rios, lagos e mares. Parte dessa água "
            "evapora, ou seja, vira vapor e sobe para a atmosfera. Quando o "
            "vapor encontra o ar mais frio lá em cima, ele se transforma em "
            "gotículas e forma as nuvens: é a condensação. Quando as "
            "gotículas ficam pesadas demais, caem na forma de chuva, neve ou "
            "granizo — isso é a precipitação. A água da chuva escorre pela "
            "superfície (escorrimento) ou penetra no solo, alimentando rios "
            "e lençóis subterrâneos.\n\n"
            "Assim, a mesma água que existia na Terra há milhões de anos "
            "continua circulando: evaporando, formando nuvens, chovendo e "
            "voltando aos rios e mares. Proteger a água — não desperdiçar e "
            "não poluir — é cuidar desse ciclo que garante a vida no planeta."
        ),
        "autor": "LeituraIA Brasil (material didático)",
        "ano": "6",
        "disciplina": "Ciências",
        "tema": "Ciclo da Água",
        "nivel": "fundamental1",
        "tipo": "expositivo",
        "genero": "artigo didático",
        "idioma": "pt-BR",
        "tags": ["água", "natureza", "ciências"],
        "bncc": [],
        "crmg": [],
        "glossario": [
            "evaporação: passagem da água do estado líquido para o gasoso.",
            "condensação: formação de gotículas de água que formam as nuvens.",
            "precipitação: queda da água na forma de chuva, neve ou granizo.",
        ],
        "perguntas": [
            Pergunta(
                pergunta="O que é o ciclo da água?",
                tipo="multipla_escolha",
                resposta="O movimento contínuo da água na natureza, mudando de lugar e de estado físico.",
            ),
            Pergunta(
                pergunta="Em que ordem acontecem os processos descritos no texto?",
                tipo="ordenacao",
                resposta="Evaporação, condensação, precipitação e escorrimento.",
            ),
            Pergunta(
                pergunta="O que podemos fazer para proteger o ciclo da água?",
                tipo="dissertativa",
                resposta="Não desperdiçar e não poluir a água.",
            ),
        ],
    },
]


def _contar_palavras(texto: str) -> int:
    return len(texto.split())


def _tempo_estimado(texto: str, ppm: int = 200) -> int:
    """Tempo estimado de leitura em minutos (~200 palavras por minuto)."""
    return max(1, round(_contar_palavras(texto) / ppm))


def _para_texto(registro: orm.TextoORM) -> TextoOut:
    return TextoOut(
        id=registro.id,
        titulo=registro.titulo,
        conteudo=registro.conteudo,
        autor=registro.autor,
        ano=registro.ano,
        disciplina=registro.disciplina,
        tema=registro.tema,
        nivel=registro.nivel,
        tipo=registro.tipo,
        genero=registro.genero,
        idioma=registro.idioma,
        tags=list(registro.tags),
        bncc=list(registro.bncc),
        crmg=list(registro.crmg),
        glossario=list(registro.glossario),
        perguntas=[Pergunta(**p) for p in registro.perguntas],
        palavras=registro.palavras,
        tempo_leitura_min=registro.tempo_leitura_min,
    )


class LibraryStore:
    """Acervo e leituras via ORM (tabelas ``textos``/``leituras``).

    ``database_url`` permite apontar outra instância (testes); sem ele vale
    ``LEITURAIA_DATABASE_URL`` ou o SQLite padrão de desenvolvimento.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self._url = database_url
        db.init_db(database_url)
        self._sementes()

    def _sementes(self) -> None:
        with db.session_scope(self._url) as sessao:
            total = int(sessao.scalar(select(func.count()).select_from(orm.TextoORM)) or 0)
        if total:
            return
        for dados in _SEED:
            self.criar(TextoCreate(**dados))

    def criar(self, dados: TextoCreate) -> TextoOut:
        texto = TextoOut(
            id=str(uuid.uuid4()),
            titulo=dados.titulo,
            conteudo=dados.conteudo,
            autor=dados.autor,
            ano=dados.ano,
            disciplina=dados.disciplina,
            tema=dados.tema,
            nivel=dados.nivel,
            tipo=dados.tipo,
            genero=dados.genero,
            idioma=dados.idioma,
            tags=list(dados.tags),
            bncc=list(dados.bncc),
            crmg=list(dados.crmg),
            glossario=list(dados.glossario),
            perguntas=list(dados.perguntas),
            palavras=_contar_palavras(dados.conteudo),
            tempo_leitura_min=_tempo_estimado(dados.conteudo),
        )
        with db.session_scope(self._url) as sessao:
            sessao.add(
                orm.TextoORM(
                    id=texto.id,
                    titulo=texto.titulo,
                    conteudo=texto.conteudo,
                    autor=texto.autor,
                    ano=texto.ano,
                    disciplina=texto.disciplina,
                    tema=texto.tema,
                    nivel=texto.nivel,
                    tipo=texto.tipo,
                    genero=texto.genero,
                    idioma=texto.idioma,
                    tags=list(texto.tags),
                    bncc=list(texto.bncc),
                    crmg=list(texto.crmg),
                    glossario=list(texto.glossario),
                    perguntas=[p.model_dump() for p in texto.perguntas],
                    palavras=texto.palavras,
                    tempo_leitura_min=texto.tempo_leitura_min,
                )
            )
        return texto

    def obter(self, texto_id: str) -> TextoOut | None:
        with db.session_scope(self._url) as sessao:
            registro = sessao.get(orm.TextoORM, texto_id)
        return _para_texto(registro) if registro is not None else None

    def deletar(self, texto_id: str) -> bool:
        with db.session_scope(self._url) as sessao:
            registro = sessao.get(orm.TextoORM, texto_id)
            if registro is None:
                return False
            sessao.delete(registro)
        return True

    def registrar_leitura(
        self,
        texto_id: str | None = None,
        usuario_id: str | None = None,
        tempo_segundos: int = 0,
        completou: bool = True,
        sessao: str | None = None,
    ) -> int:
        """Grava uma leitura e devolve o total acumulado.

        ``sessao`` é a chave de idempotência do Leitor Digital público: a mesma
        visita (mesmo texto + sessão) é gravada uma única vez. Leituras com
        ``sessao`` nula (endpoint autenticado) sempre contam.
        """
        with db.session_scope(self._url) as sessao_db:
            try:
                with sessao_db.begin_nested():
                    sessao_db.add(
                        orm.LeituraORM(
                            texto_id=texto_id,
                            usuario_id=usuario_id,
                            tempo_segundos=int(tempo_segundos),
                            completou=completou,
                            sessao=sessao,
                            criado_em=datetime.now(UTC),
                        )
                    )
            except IntegrityError:
                # Mesma visita (texto + sessão) já registrada: não conta de novo.
                pass
            return int(sessao_db.scalar(select(func.count()).select_from(orm.LeituraORM)) or 0)

    @property
    def total_leituras(self) -> int:
        with db.session_scope(self._url) as sessao:
            return int(sessao.scalar(select(func.count()).select_from(orm.LeituraORM)) or 0)

    @property
    def total_textos(self) -> int:
        with db.session_scope(self._url) as sessao:
            return int(sessao.scalar(select(func.count()).select_from(orm.TextoORM)) or 0)

    def listar(self, **filtros: Any) -> list[TextoOut]:
        """Filtros: disciplina, ano, tema, nivel, tipo, genero, idioma,
        tags, bncc, crmg, palavras_min, palavras_max, tempo_min, tempo_max."""
        consulta = select(orm.TextoORM)

        disciplina = filtros.get("disciplina")
        if disciplina:
            consulta = consulta.where(
                func.lower(orm.TextoORM.disciplina) == str(disciplina).lower()
            )

        ano = filtros.get("ano")
        if ano:
            anos = [a.strip() for a in str(ano).split(",") if a.strip()]
            if anos:
                consulta = consulta.where(orm.TextoORM.ano.in_(anos))

        tema = filtros.get("tema")
        if tema:
            consulta = consulta.where(func.lower(orm.TextoORM.tema).like(f"%{str(tema).lower()}%"))

        for campo in ("nivel", "tipo", "genero", "idioma"):
            valor = filtros.get(campo)
            if valor:
                consulta = consulta.where(getattr(orm.TextoORM, campo) == valor)

        palavras_min = filtros.get("palavras_min")
        if palavras_min is not None:
            consulta = consulta.where(orm.TextoORM.palavras >= int(palavras_min))
        palavras_max = filtros.get("palavras_max")
        if palavras_max is not None:
            consulta = consulta.where(orm.TextoORM.palavras <= int(palavras_max))

        tempo_min = filtros.get("tempo_min")
        if tempo_min is not None:
            consulta = consulta.where(orm.TextoORM.tempo_leitura_min >= int(tempo_min))
        tempo_max = filtros.get("tempo_max")
        if tempo_max is not None:
            consulta = consulta.where(orm.TextoORM.tempo_leitura_min <= int(tempo_max))

        consulta = consulta.order_by(func.lower(orm.TextoORM.titulo))

        with db.session_scope(self._url) as sessao:
            textos = [_para_texto(registro) for registro in sessao.scalars(consulta).all()]

        # Listas guardadas como JSON: filtro em Python (poucos textos por consulta).
        tags = filtros.get("tags")
        if tags:
            alvo = [s.strip().lower() for s in str(tags).split(",") if s.strip()]
            textos = [t for t in textos if any(tag in [x.lower() for x in t.tags] for tag in alvo)]

        bncc = filtros.get("bncc")
        if bncc:
            alvo_bncc = [s.strip().upper() for s in str(bncc).split(",") if s.strip()]
            textos = [t for t in textos if set(alvo_bncc) & set(t.bncc)]

        crmg = filtros.get("crmg")
        if crmg:
            alvo_crmg = [s.strip().upper() for s in str(crmg).split(",") if s.strip()]
            textos = [t for t in textos if set(alvo_crmg) & set(t.crmg)]

        return textos

    def habilidades(self) -> list[str]:
        with db.session_scope(self._url) as sessao:
            listas = sessao.scalars(select(orm.TextoORM.bncc)).all()
        habilidades: set[str] = set()
        for lista in listas:
            habilidades.update(lista or [])
        return sorted(habilidades)


_library: LibraryStore | None = None


def get_library() -> LibraryStore:
    global _library
    if _library is None:
        _library = LibraryStore()
    return _library


def seeds():
    """Reimportável para testes — devolve a lista de seeds (cópia)."""
    return [dict(s) for s in _SEED]


__all__ = ["LibraryStore", "get_library", "seeds"]
