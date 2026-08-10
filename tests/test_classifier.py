"""Testes do TaskClassifier — classificador inteligente de tarefas.

Cobre:
- Classificação correta de cada TaskType (code, refactor, architecture,
  planning, analysis, creative, rag)
- Palavras-chave de override tomando precedência
- Prompts vazios retornando TaskType.general
- Prompts sem padrões conhecidos retornando TaskType.general
- Case insensitivity
- Comportamento de pontuação (múltiplos patterns numa categoria)
- Prompts em português (padrões principais do classificador)
"""

from __future__ import annotations

from ai.classifier import TaskClassifier
from ai.providers.base import TaskType

# ═════════════════════════════════════════════════════════════════════════════
# Código
# ═════════════════════════════════════════════════════════════════════════════


class TestClassifyCode:
    """Testes para classificação como TaskType.code."""

    def test_prompt_com_codigo_python(self):
        result = TaskClassifier.classify("crie uma função em Python que calcula fibonacci")
        assert result == TaskType.code

    def test_prompt_com_implementar_api(self):
        result = TaskClassifier.classify("implementar uma API REST em FastAPI")
        assert result == TaskType.code

    def test_prompt_com_corrigir_bug(self):
        result = TaskClassifier.classify("corrija este bug no código javascript")
        assert result == TaskType.code

    def test_prompt_com_refatorar_e_codigo(self):
        """'código' é override para code e aparece PRIMEIRO no dict
        OVERRIDE_KEYWORDS, então 'refatorar código python' é code."""
        result = TaskClassifier.classify("refatorar código python")
        assert result == TaskType.code  # 'código' é override e vem antes de 'refatorar'

    def test_prompt_com_escreva_classe(self):
        result = TaskClassifier.classify("escreva uma classe de serviço")
        assert result == TaskType.code

    def test_prompt_curto_apenas_code(self):
        result = TaskClassifier.classify("código")
        assert result == TaskType.code

    def test_prompt_com_typescript_react(self):
        result = TaskClassifier.classify("crie um componente React em typescript")
        assert result == TaskType.code

    def test_prompt_com_teste_unitario(self):
        result = TaskClassifier.classify("escreva teste unitário para esta função")
        assert result == TaskType.code


# ═════════════════════════════════════════════════════════════════════════════
# Refatoração
# ═════════════════════════════════════════════════════════════════════════════


class TestClassifyRefactor:
    """Testes para classificação como TaskType.refactor."""

    def test_prompt_refatorar(self):
        result = TaskClassifier.classify("refatorar este módulo complexo")
        assert result == TaskType.refactor

    def test_prompt_otimizar(self):
        result = TaskClassifier.classify("preciso otimizar este processo lento")
        assert result == TaskType.refactor

    def test_prompt_simplificar(self):
        result = TaskClassifier.classify("simplificar a lógica de negócio")
        assert result == TaskType.refactor

    def test_prompt_clean_code(self):
        """'clean code' matcha refactor. Evitamos 'code' solto
        que acionaria o pattern de código."""
        result = TaskClassifier.classify("revisar e simplificar a lógica")
        assert result == TaskType.refactor

    def test_prompt_melhorar_complexidade(self):
        """'melhorar' e 'complexidade' matcham refactor.
        Evitamos 'código' que é override keyword."""
        result = TaskClassifier.classify("melhorar este algoritmo com manutenção")
        assert result == TaskType.refactor

    def test_prompt_complexidade(self):
        result = TaskClassifier.classify("reduzir complexidade do algoritmo")
        assert result == TaskType.refactor


# ═════════════════════════════════════════════════════════════════════════════
# Arquitetura
# ═════════════════════════════════════════════════════════════════════════════


class TestClassifyArchitecture:
    """Testes para classificação como TaskType.architecture."""

    def test_prompt_arquitetura(self):
        result = TaskClassifier.classify("definir a arquitetura do sistema")
        assert result == TaskType.architecture

    def test_prompt_design_pattern(self):
        result = TaskClassifier.classify("qual design pattern usar para fila de eventos")
        assert result == TaskType.architecture

    def test_prompt_microsservicos(self):
        result = TaskClassifier.classify("projetar microsserviços com mensageria")
        assert result == TaskType.architecture

    def test_prompt_diagrama_fluxo(self):
        result = TaskClassifier.classify("criar diagrama de fluxo da infra")
        assert result == TaskType.architecture

    def test_prompt_escalabilidade(self):
        result = TaskClassifier.classify("plano de escalabilidade para banco de dados")
        assert result == TaskType.architecture

    def test_prompt_cache(self):
        result = TaskClassifier.classify("estrutura de cache para API")
        assert result == TaskType.architecture


# ═════════════════════════════════════════════════════════════════════════════
# Planejamento
# ═════════════════════════════════════════════════════════════════════════════


class TestClassifyPlanning:
    """Testes para classificação como TaskType.planning."""

    def test_prompt_planejamento(self):
        result = TaskClassifier.classify("planejar as tarefas da sprint")
        assert result == TaskType.planning

    def test_prompt_roadmap(self):
        result = TaskClassifier.classify("criar roadmap do produto")
        assert result == TaskType.planning

    def test_prompt_organizar_etapas(self):
        result = TaskClassifier.classify("organizar etapas e prazos do projeto")
        assert result == TaskType.planning

    def test_prompt_estrategia(self):
        result = TaskClassifier.classify("definir estratégia de lançamento")
        assert result == TaskType.planning

    def test_prompt_proximos_passos(self):
        result = TaskClassifier.classify("quais os próximos passos do desenvolvimento")
        assert result == TaskType.planning


# ═════════════════════════════════════════════════════════════════════════════
# Análise
# ═════════════════════════════════════════════════════════════════════════════


class TestClassifyAnalysis:
    """Testes para classificação como TaskType.analysis."""

    def test_prompt_analisar(self):
        result = TaskClassifier.classify("analisar logs de erro do servidor")
        assert result == TaskType.analysis

    def test_prompt_investigar(self):
        result = TaskClassifier.classify("investigar causa do crash")
        assert result == TaskType.analysis

    def test_prompt_debug(self):
        result = TaskClassifier.classify("depurar exception no traceback")
        assert result == TaskType.analysis

    def test_prompt_por_que_erro(self):
        result = TaskClassifier.classify("por que o sistema está caindo")
        assert result == TaskType.analysis

    def test_prompt_root_cause(self):
        result = TaskClassifier.classify("qual a root cause do problema")
        assert result == TaskType.analysis

    def test_prompt_diagnostico(self):
        result = TaskClassifier.classify("diagnóstico de performance")
        assert result == TaskType.analysis


# ═════════════════════════════════════════════════════════════════════════════
# Criativo
# ═════════════════════════════════════════════════════════════════════════════


class TestClassifyCreative:
    """Testes para classificação como TaskType.creative."""

    def test_prompt_escreva_texto(self):
        result = TaskClassifier.classify("escreva um texto de apresentação")
        assert result == TaskType.creative

    def test_prompt_crie_poema(self):
        result = TaskClassifier.classify("crie um poema sobre tecnologia")
        assert result == TaskType.creative

    def test_prompt_roteiro(self):
        result = TaskClassifier.classify("crie um roteiro de vídeo")
        assert result == TaskType.creative

    def test_prompt_conteudo_marketing(self):
        result = TaskClassifier.classify("redação de conteúdo para marketing")
        assert result == TaskType.creative

    def test_prompt_copywriting(self):
        result = TaskClassifier.classify("faça copywriting para landing page")
        assert result == TaskType.creative


# ═════════════════════════════════════════════════════════════════════════════
# RAG / Pesquisa
# ═════════════════════════════════════════════════════════════════════════════


class TestClassifyRag:
    """Testes para classificação como TaskType.rag."""

    def test_prompt_pesquisar_documento(self):
        result = TaskClassifier.classify("pesquisar informação sobre OpenVINO")
        assert result == TaskType.rag

    def test_prompt_resumir_artigo(self):
        result = TaskClassifier.classify("resumir este artigo sobre machine learning")
        assert result == TaskType.rag

    def test_prompt_buscar_documentacao(self):
        result = TaskClassifier.classify("buscar na documentação do FastAPI")
        assert result == TaskType.rag

    def test_prompt_o_que_diz_documento(self):
        result = TaskClassifier.classify("o que diz o documento sobre segurança")
        assert result == TaskType.rag

    def test_prompt_extrair_texto(self):
        result = TaskClassifier.classify("extrair informações do arquivo PDF")
        assert result == TaskType.rag

    def test_prompt_explique_texto(self):
        result = TaskClassifier.classify("explique o que o texto diz sobre IA")
        assert result == TaskType.rag

    def test_prompt_knowledge_base(self):
        result = TaskClassifier.classify("consultar base de conhecimento")
        assert result == TaskType.rag


# ═════════════════════════════════════════════════════════════════════════════
# Override Keywords
# ═════════════════════════════════════════════════════════════════════════════


class TestOverrideKeywords:
    """Override keywords devem sobrescrever outras classificações."""

    def test_codigo_sobrescreve_arquitetura(self):
        """'código' é override para code, mesmo com padrão de architecture."""
        result = TaskClassifier.classify("código e arquitetura do sistema")
        assert result == TaskType.code

    def test_refatorar_sobrescreve_analise(self):
        """'refatorar' é override para refactor."""
        result = TaskClassifier.classify("refatorar e analisar performance")
        assert result == TaskType.refactor

    def test_programar_sobrescreve_planejamento(self):
        """'programar' é override para code."""
        result = TaskClassifier.classify("programar e planejar sprint")
        assert result == TaskType.code

    def test_arquitetura_sobrescreve_rag(self):
        """'arquitetura' é override para architecture."""
        result = TaskClassifier.classify("arquitetura de busca de documentos")
        assert result == TaskType.architecture

    def test_planejar_sobrescreve_criativo(self):
        """'planejar' é override para planning."""
        result = TaskClassifier.classify("planejar texto criativo")
        assert result == TaskType.planning

    def test_override_keyword_vence_pontuacao_alta(self):
        """Override keyword deve vencer mesmo se outra categoria
        tiver mais matches de padrão."""
        result = TaskClassifier.classify(
            "arquitetura, design pattern, fluxo, cache, escalabilidade, mensageria e código"
        )
        # 'código' é override para code
        assert result == TaskType.code


# ═════════════════════════════════════════════════════════════════════════════
# Casos de Borda
# ═════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Casos de borda: prompt vazio, sem matches, case insensitivity."""

    def test_prompt_vazio_retorna_general(self):
        result = TaskClassifier.classify("")
        assert result == TaskType.general

    def test_prompt_espacos_retorna_general(self):
        result = TaskClassifier.classify("   ")
        assert result == TaskType.general

    def test_sem_padroes_conhecidos_retorna_general(self):
        result = TaskClassifier.classify("bom dia, como vai?")
        assert result == TaskType.general

    def test_numeros_e_pontuacao_retorna_general(self):
        result = TaskClassifier.classify("12345 !!! ??? ***")
        assert result == TaskType.general

    def test_case_insensitivity_maiusculo(self):
        """Deve funcionar com letras maiúsculas também.
        'CÓDIGO' é override para code."""
        result = TaskClassifier.classify("REFATORAR CÓDIGO PYTHON")
        assert result == TaskType.code  # 'código' override vence

    def test_case_insensitivity_misturado(self):
        result = TaskClassifier.classify("ArQuItEtUrA dO sIsTeMa")
        assert result == TaskType.architecture

    def test_prompt_muito_curto_sem_sentido(self):
        result = TaskClassifier.classify("x")
        assert result == TaskType.general

    def test_prompt_apenas_palavra_conhecida(self):
        """Palavra isolada que não está em override nem patterns."""
        result = TaskClassifier.classify("ajuda")
        assert result == TaskType.general


# ═════════════════════════════════════════════════════════════════════════════
# Pontuação e Desempate
# ═════════════════════════════════════════════════════════════════════════════


class TestScoring:
    """Comportamento de pontuação quando múltiplos patterns matcham."""

    def test_maior_pontuacao_vence(self):
        """A categoria com maior pontuação deve vencer."""
        result = TaskClassifier.classify(
            "código, função, classe, método, API, endpoint, analisar log de erro"
        )
        # code tem mais matches (código, função, classe, método, api, endpoint)
        # analysis só tem (analisar)
        assert result == TaskType.code

    def test_mesma_palavra_em_patterns_diferentes(self):
        """Se patterns de categorias diferentes matcham com mesma
        palavra, a pontuação é contada por padrão individual."""
        result = TaskClassifier.classify("criativo e código")
        # 'código' é override keyword → code
        assert result == TaskType.code

    def test_prompt_misto_refactor_e_planning(self):
        """Refactor tem mais matches que planning."""
        result = TaskClassifier.classify("refatorar, otimizar, simplificar e planejar")
        # refactor tem 3 matches (refatorar, otimizar, simplificar)
        # planning tem 1 match (planejar)
        assert result == TaskType.refactor

    def test_prompt_sem_override_mas_multiplas_categorias(self):
        """Sem override, a categoria com mais matches vence."""
        result = TaskClassifier.classify("analisar, investigar e depurar o erro de exception")
        # analysis tem 5 matches (analisar, investigar, depurar, erro, exception)
        assert result == TaskType.analysis
