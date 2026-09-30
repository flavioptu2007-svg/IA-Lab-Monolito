"""Testes da biblioteca de textos do LeituraIA Brasil."""


from leituraia.library import LibraryStore, _contar_palavras, _tempo_estimado
from leituraia.models import TextoCreate


def _texto(**overrides) -> TextoCreate:
    base = dict(
        titulo="Texto de teste",
        conteudo="Palavra " * 50,  # 50 palavras
        ano="7",
        disciplina="História",
        tema="Feudalismo",
        nivel="fundamental2",
    )
    base.update(overrides)
    return TextoCreate(**base)


class TestHelpers:
    def test_contar_palavras(self):
        assert _contar_palavras("um dois três") == 3
        assert _contar_palavras("") == 0

    def test_tempo_estimado_minimo_1_minuto(self):
        assert _tempo_estimado("uma palavra") == 1
        assert _tempo_estimado("palavra " * 400) == 2  # 400/200


class TestLibraryStore:
    def test_sementes_carregadas(self):
        lib = LibraryStore()
        assert lib.total_textos >= 1

    def test_criar_e_obter(self):
        lib = LibraryStore()
        criado = lib.criar(_texto())
        obtido = lib.obter(criado.id)
        assert obtido is not None
        assert obtido.titulo == "Texto de teste"
        assert obtido.palavras == 50
        assert obtido.tempo_leitura_min == 1

    def test_deletar(self):
        lib = LibraryStore()
        criado = lib.criar(_texto())
        assert lib.deletar(criado.id) is True
        assert lib.obter(criado.id) is None
        assert lib.deletar(criado.id) is False

    def test_registrar_leitura(self):
        lib = LibraryStore()
        antes = lib.total_leituras
        assert lib.registrar_leitura() == antes + 1
        assert lib.total_leituras == antes + 1

    def test_listar_por_disciplina_case_insensitive(self):
        lib = LibraryStore()
        lib.criar(_texto(disciplina="História"))
        resultados = lib.listar(disciplina="história")
        assert all(t.disciplina.lower() == "história" for t in resultados)
        assert resultados

    def test_listar_por_nivel(self):
        lib = LibraryStore()
        lib.criar(_texto(nivel="tea"))
        resultados = lib.listar(nivel="tea")
        assert all(t.nivel == "tea" for t in resultados)

    def test_listar_por_tema_inexistente_vazio(self):
        lib = LibraryStore()
        assert lib.listar(tema="Tema Que Nunca Existiu") == []
