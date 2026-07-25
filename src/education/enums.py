"""Enums educacionais — Anos letivos, BNCC, tipos de avaliação e mais.

Migrado do projeto HistóriaIA (AI/historiaia/) com adaptações
para o monolito unificado.
"""

from __future__ import annotations

from enum import StrEnum

# ═══════════════════════════════════════════════════════════════
# Acadêmicos
# ═══════════════════════════════════════════════════════════════


class AcademicYear(StrEnum):
    """Anos/séries do ensino básico brasileiro."""

    EF_6 = "6º ano EF"
    EF_7 = "7º ano EF"
    EF_8 = "8º ano EF"
    EF_9 = "9º ano EF"
    EM_1 = "1º ano EM"
    EM_2 = "2º ano EM"
    EM_3 = "3º ano EM"
    EJA_1 = "EJA 1º segmento"
    EJA_2 = "EJA 2º segmento"
    EJA_3 = "EJA 3º segmento"


class Trimester(StrEnum):
    """Trimestres letivos."""

    T1 = "1º Trimestre"
    T2 = "2º Trimestre"
    T3 = "3º Trimestre"


class Shift(StrEnum):
    """Turnos escolares."""

    MORNING = "Matutino"
    AFTERNOON = "Vespertino"
    EVENING = "Noturno"
    FULL = "Integral"


class Weekday(StrEnum):
    """Dias da semana letivos."""

    MONDAY = "Segunda-feira"
    TUESDAY = "Terça-feira"
    WEDNESDAY = "Quarta-feira"
    THURSDAY = "Quinta-feira"
    FRIDAY = "Sexta-feira"
    SATURDAY = "Sábado"


class ClassPeriod(StrEnum):
    """Duração das aulas."""

    REGULAR = "50 min"
    DOUBLE = "100 min"


class EvaluationType(StrEnum):
    """Tipos de avaliação."""

    EXAM = "Prova"
    QUIZ = "Quiz"
    ESSAY = "Redação"
    ORAL = "Oral"
    PROJECT = "Projeto"
    ACTIVITY = "Atividade"
    RECOVERY = "Recuperação"


class LessonMoment(StrEnum):
    """Momentos pedagógicos de uma aula."""

    INTRODUCTION = "Introdução"
    DEVELOPMENT = "Desenvolvimento"
    CLOSURE = "Conclusão"


class ActivityType(StrEnum):
    """Tipos de atividades didáticas."""

    FLASHCARD = "Flashcard"
    DOMINO = "Dominó"
    BINGO = "Bingo"
    TIMELINE = "Linha do tempo"
    DEBATE = "Debate"
    SIMULATION = "Simulação"
    MAP = "Mapa conceitual"
    TEXT_ANALYSIS = "Análise de texto"
    IMAGE_ANALYSIS = "Análise de imagem"
    RESEARCH = "Pesquisa"
    GAMIFICATION = "Gamificação"
    OTHER = "Outro"


class LessonPlanStatus(StrEnum):
    """Status do plano de aula."""

    DRAFT = "Rascunho"
    REVIEW = "Em revisão"
    APPROVED = "Aprovado"
    ARCHIVED = "Arquivado"


# ═══════════════════════════════════════════════════════════════
# BNCC — Base Nacional Comum Curricular (História)
# ═══════════════════════════════════════════════════════════════


class BNCCCompetence(StrEnum):
    """Competências específicas de História (BNCC)."""

    CE01 = "Identificar e contextualizar"
    CE02 = "Compreender e comparar"
    CE03 = "Analisar e interpretar"
    CE04 = "Relacionar e problematizar"
    CE05 = "Questionar e criticar"
    CE06 = "Argumentar e posicionar-se"
    CE07 = "Valorizar e preservar"
    CE08 = "Agir com ética e cidadania"


class BNCCObjectKnowledge(StrEnum):
    """Objetos de conhecimento da BNCC de História."""

    # 6º ano
    EF06_ANTIGUIDADE = "Antiguidade Clássica"
    EF06_MEDIEVO = "Idade Média"
    EF06_AFRICA = "África antiga"
    EF06_BRASIL_INDIGENA = "Brasil indígena"
    EF06_ORIENTE = "Oriente Médio"

    # 7º ano
    EF07_MODERNA = "Idade Moderna"
    EF07_EXPANSAO = "Expansão marítima"
    EF07_BRASIL_COLONIAL = "Brasil colonial"
    EF07_AFRICA_MODERNA = "África moderna"
    EF07_REFORMA = "Reforma e Contrarreforma"

    # 8º ano
    EF08_ILUMINISMO = "Iluminismo"
    EF08_REVOLUCOES = "Revoluções burguesas"
    EF08_BRASIL_IMPERIO = "Brasil Império"
    EF08_AMERICAS = "Américas no século XIX"
    EF08_TRABALHO = "Trabalho e escravidão"

    # 9º ano
    EF09_REPUBLICA = "República no Brasil"
    EF09_MUNDO_CONTEMPORANEO = "Mundo contemporâneo"
    EF09_GUERRAS = "Guerras mundiais"
    EF09_DITADURAS = "Ditaduras na América Latina"
    EF09_GLOBALIZACAO = "Globalização"

    # Ensino Médio
    EM_BRASIL_RECENTE = "Brasil recente"
    EM_GEOPOLITICA = "Geopolítica mundial"
    EM_DIREITOS = "Direitos humanos"
    EM_DIVERSIDADE = "Diversidade cultural"


# ═══════════════════════════════════════════════════════════════
# Dados de apoio
# ═══════════════════════════════════════════════════════════════

# Mapeamento de códigos de habilidade BNCC para descrições
BNCC_SKILLS: dict[str, str] = {
    "EF06HI01": "Identificar diferentes formas de compreensão da noção de tempo",
    "EF06HI02": "Identificar a importância das fontes históricas",
    "EF06HI03": "Identificar as hipóteses científicas sobre origem dos seres humanos",
    "EF06HI04": "Conhecer as teorias sobre a origem do homem americano",
    "EF06HI05": "Descrever modos de vida dos primeiros grupos humanos",
    "EF06HI06": "Identificar as transformações ocorridas no processo de sedentarização",
    "EF07HI01": "Explicar o significado de 'modernidade' e suas lógicas",
    "EF07HI02": "Identificar conexões entre Europa, América e África",
    "EF07HI03": "Analisar a formação dos estados nacionais modernos",
    "EF07HI04": "Identificar o processo de expansão marítima europeia",
    "EF07HI05": "Analisar o encontro entre europeus e povos americanos",
    "EF08HI01": "Identificar as características do Antigo Regime",
    "EF08HI02": "Analisar as revoluções inglesas do século XVII",
    "EF08HI03": "Analisar a Revolução Francesa e seus desdobramentos",
    "EF08HI04": "Analisar o processo de independência do Brasil",
    "EF08HI05": "Explicar o Primeiro Reinado e Período Regencial",
    "EF09HI01": "Analisar o processo de Proclamação da República",
    "EF09HI02": "Caracterizar a Primeira República no Brasil",
    "EF09HI03": "Analisar a Era Vargas e seu contexto",
    "EF09HI04": "Analisar a Segunda Guerra Mundial",
    "EF09HI05": "Analisar o período da Ditadura Militar no Brasil",
    "EM13CHS101": "Analisar processos políticos e econômicos da contemporaneidade",
    "EM13CHS102": "Identificar as transformações do mundo do trabalho",
    "EM13CHS103": "Analisar as relações de poder na sociedade contemporânea",
    "EM13CHS201": "Analisar impactos das tecnologias na sociedade",
    "EM13CHS202": "Analisar as relações de produção e consumo",
    "EM13CHS301": "Analisar a organização do Estado e suas instituições",
    "EM13CHS302": "Analisar os fundamentos do Estado Democrático de Direito",
    "EM13CHS401": "Analisar as manifestações culturais e suas transformações",
    "EM13CHS402": "Valorizar a diversidade cultural brasileira",
    "EM13CHS501": "Analisar os conflitos e desigualdades do mundo contemporâneo",
    "EM13CHS502": "Analisar as lutas pelos direitos humanos",
    "EM13CHS601": "Analisar ações de promoção do desenvolvimento sustentável",
}
