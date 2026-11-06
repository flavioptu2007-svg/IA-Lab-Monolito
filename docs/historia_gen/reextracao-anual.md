# Reextração anual do catálogo CRMG — do download ao teste de reprodução

Procedimento para atualizar o catálogo fechado de habilidades quando a SEE-MG
publica uma versão nova do Currículo Referência. O princípio é o mesmo do
pipeline: **falha fechada** — nenhum passo adivinha; se a conferência não
fechar, o catálogo continua inválido para geração.

**Quando rodar:** no início de cada ano letivo, ou assim que
`catalogo-validar` imprimir o aviso de `data_acesso` de ano anterior.

**Tempo estimado:** 15 min quando o documento **não** mudou (só reconfirmação);
meio dia quando mudou (reextração + conferência das 97 linhas + regeneração dos
derivados).

**Regra de ouro:** a lista de habilidades nunca é editada à mão — ela é saída do
extrator. Edição manual é desfeita na próxima extração, sem aviso.

---

## Passo 1 — Baixar o PDF oficial

Página institucional:
<https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/curriculo-referencia-de-minas-gerais>

Baixe o PDF "Versão atualizada" (hoje em
`/wp-content/uploads/2026/05/CRMG-Infantil-e-Ensino-Fundamental-_Versao-atualizada.pdf`
— a URL muda quando o site republica, então copie o link do botão, não o
histórico) e salve por cima da cópia versionada:

```bash
# fora do repositório, para não sobrescrever antes da conferência
mv ~/Downloads/CRMG*.pdf /tmp/crmg_novo.pdf
```

## Passo 2 — Comparar os hashes antes de qualquer coisa

```bash
md5sum /tmp/crmg_novo.pdf
sha256sum /tmp/crmg_novo.pdf
```

Compare com o que está registrado em
`src/historia_gen/catalogo/dados/catalogo_crmg_ef_anos_finais.json` →
`meta.pdf_md5` e `meta.pdf_sha256` (e com a seção "Identificação da fonte" de
[`fonte_oficial.md`](../../src/historia_gen/catalogo/fonte_oficial.md)).

| Resultado | O que significa | Vá para |
|---|---|---|
| **Os dois hashes batem** | o site republicou o mesmo conteúdo — **nada mudou** | Passo 3 |
| **Algum hash difere** | documento novo (ou só reimpresso; o passo 5 diz como saber) | Passo 4 |

Nunca compare "de olho" o texto do PDF: hash igual é prova de conteúdo igual, e
o `catalogo-validar` usa exatamente esses dois valores.

## Passo 3 — Reconferência sem mudança de conteúdo

O catálogo continua válido; só a data de acesso envelheceu e o aviso anual
apareceria.

1. Copie o PDF novo por cima do versionado (os bytes são iguais, mas a cópia
   confirma que o arquivo do repositório é o que está publicado):

   ```bash
   cp /tmp/crmg_novo.pdf src/historia_gen/catalogo/dados/fonte_oficial/crmg_infantil_ef.pdf
   ```

2. Atualize `meta.data_acesso` para a data de hoje no JSON do catálogo. **Não**
   mexa em `revisao_aprovada` nem em `revisado_por`: a conferência do professor
   continua valendo, porque o conteúdo é o mesmo.

3. Regenere o que carrega a data (o teste de atualidade do `.docx` quebra se
   você esquecer) e revalide:

   ```bash
   python3 -m src.historia_gen conferencia-docx
   python3 -m src.historia_gen catalogo-validar
   ```

4. Registre a reconferência em [`validacoes.md`](validacoes.md) (seção Q2): data,
   hashes conferidos e "conteúdo inalterado".

## Passo 4 — Documento novo: substituir a fonte e reextrair

1. Guarde o PDF antigo para comparação (não versionado):

   ```bash
   cp src/historia_gen/catalogo/dados/fonte_oficial/crmg_infantil_ef.pdf /tmp/crmg_antigo.pdf
   cp /tmp/crmg_novo.pdf src/historia_gen/catalogo/dados/fonte_oficial/crmg_infantil_ef.pdf
   ```

2. Rode a extração **para fora do repositório**, para inspecionar antes de
   aceitar (sem `--saida`, ela grava em `catalogo/dados/rascunho_extracao.json`):

   ```bash
   python3 -m src.historia_gen catalogo-extrair --saida /tmp/rascunho_extracao.json
   ```

   Requer a dependência de dev `pymupdf` (já vem em `.[dev]`).

## Passo 5 — Ler a saída do extrator

Saída normal (sobre o PDF de 2023, que é o versionado):

```
códigos no texto bruto: 103 | células extraídas: 103 | no escopo Anos Finais: 97
por ano (escopo): {'6º ano EF': 19, '7º ano EF': 17, '8º ano EF': 27, '9º ano EF': 34}
contagem 6º ano EF: 19 (registrado 19) ✓
...
rascunho gravado em /tmp/rascunho_extracao.json — revisão manual obrigatória antes do uso
```

Como interpretar:

* **`códigos no texto bruto` ≠ `células extraídas`** → alguma célula não foi
  lida: a extração está incompleta, o comando sai com código 1. Não aceite o
  rascunho.
* **`DUPLICADOS`** → a grade do PDF mudou e uma célula foi lida duas vezes.
* **`SEM ANO IDENTIFICADO`** → a coluna ANO perdeu a fronteira; o ano é
  obrigatório no catálogo.
* **`avisos`** → célula da coluna Habilidades sem código legível. Cada aviso traz
  a página física e a coordenada; confira nessa página.
* **`DIVERGENTE`** nas contagens → **esperado** quando o documento realmente
  mudou (a contraprova é contra o catálogo antigo). Significa: conte as
  habilidades no PDF, por ano, e confirme o número novo antes de seguir.

### Quando o problema é de página, não de texto

O extrator assume a diagramação do PDF atual: janela de páginas físicas
`FIS_INICIO..FIS_FIM` (566 a 578) e faixas de coluna `STRIPS` (coordenadas x de
ANO/Unidades/Objetos/Habilidades), além de `OFFSET_IMPRESSA = -1`. Se o documento
novo tiver outra paginação ou outro alinhamento de colunas, **todos** os itens
acima vão falhar juntos (células vazias, sem ano, contagem zero).

Nesse caso a correção é no `src/historia_gen/catalogo/extraidor.py`: localize o
Organizador Curricular de História no PDF novo (seção 15), anote a primeira e a
última página **física** da tabela e as coordenadas x das quatro colunas, e
ajuste as constantes. Isso é mudança de código, com teste — não configuração.

## Passo 6 — Montar o catálogo novo a partir do rascunho

Depois de conferir as contagens no PDF, grave o catálogo com um script — não
editando o JSON à mão. Ele preserva o `meta`, atualiza hashes e contagens, troca a
lista de habilidades pelo rascunho e **fecha o gate** (`revisao_aprovada: false`),
porque o conteúdo deixou de ser o conferido pelo professor.

```bash
python3 - <<'PY'
import hashlib
import json
from datetime import date
from pathlib import Path

dados = Path("src/historia_gen/catalogo/dados")
catalogo = json.loads((dados / "catalogo_crmg_ef_anos_finais.json").read_text(encoding="utf-8"))
rascunho = json.loads(Path("/tmp/rascunho_extracao.json").read_text(encoding="utf-8"))
bruto = (dados / "fonte_oficial" / "crmg_infantil_ef.pdf").read_bytes()

meta = catalogo["meta"]
meta["pdf_md5"] = hashlib.md5(bruto, usedforsecurity=False).hexdigest()
meta["pdf_sha256"] = hashlib.sha256(bruto).hexdigest()
meta["data_acesso"] = date.today().isoformat()
meta["extraido_em"] = date.today().isoformat()
meta["revisao_aprovada"] = False
meta["revisado_por"] = None
meta["revisao_metodo"] = ""
meta["revisao_data"] = ""

contagens = {}
for h in rascunho["habilidades"]:
    contagens[h["ano"]] = contagens.get(h["ano"], 0) + 1
meta["contagens_esperadas"] = dict(sorted(contagens.items()))

catalogo["habilidades"] = rascunho["habilidades"]
(dados / "catalogo_crmg_ef_anos_finais.json").write_text(
    json.dumps(catalogo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
)
print("contagens gravadas:", meta["contagens_esperadas"])
PY
```

Confira o que saiu **antes** de validar: as contagens impressas têm de ser as que
você contou no PDF no passo 5. Se não forem, o problema é de extração — volte ao
passo 5, não ajuste o JSON.

Depois atualize à mão o que o script não decide: `meta.versao` (a frase do site),
`meta.url_pdf` (a URL nova, se mudou) e `meta.anomalias_do_documento` (as
anomalias do documento novo, ou "nenhuma"). Registre as anomalias também em
[`fonte_oficial.md`](../../src/historia_gen/catalogo/fonte_oficial.md).

## Passo 7 — Ajustar o que está amarrado ao documento antigo

O conteúdo mudou; estes pontos são **prosa ou constante** que o extrator não
reescreve:

| Onde | O que atualizar |
|---|---|
| `tests/test_historia_gen_catalogo.py` → `CONTAGENS_ESPERADAS` | as quatro contagens novas (é a contraprova independente do JSON) |
| `docs/historia_gen/roteiro-conferencia-catalogo.md` | a faixa de páginas do organizador (seção 2) e a tabela página→códigos (seção 4) |
| `docs/historia_gen/conferencia_catalogo.csv` | regerar (comando na seção "Regenerando o CSV", no roteiro) |
| `docs/historia_gen/roteiro-conferencia-catalogo.docx` | `python3 -m src.historia_gen conferencia-docx` |
| `tests/test_historia_gen_cli.py` → `test_catalogo_versionado_existe_no_repositorio` | nada: o catálogo novo nasce com `revisao_aprovada: false`, então a asserção `is True` falha até a aprovação — é o lembrete correto do gate fechado |

## Passo 8 — Teste de reprodução (o portão de verdade)

```bash
python3 -m src.historia_gen catalogo-validar
python3 -m pytest -q tests/test_historia_gen_catalogo.py
```

O que cada checagem prova:

* **`catalogo-validar`** — estrutura, códigos únicos, hashes recalculados do PDF
versionado, contagens por ano contra `meta.contagens_esperadas`, páginas dentro
do PDF e o estado da revisão (pendente ou aprovada). Fecha se qualquer coisa
divergir.
* **`test_extrator_reproduz_o_catalogo_versionado`** — reextrai o PDF versionado
  em memória e compara **linha a linha** (código, descrição, ano, unidade,
  objeto, página, tipo de modificação) com o catálogo gravado. É a prova de que o
  JSON não foi editado à mão e de que a extração continua determinística.
* **`test_catalogo_versionado_contagem_por_ano`** e
  **`test_catalogo_versionado_hashes_conferem_com_pdf`** — contraprovas
  independentes das duas anteriores.
* **`test_csv_de_conferencia_acompanha_o_catalogo`** e
  **`test_docx_de_conferencia_esta_atualizado`** — falham se os derivados não
  foram regerados.

Se o teste de reprodução falhar com o catálogo recém-gerado, a mensagem mostra a
primeira linha divergente: quase sempre é `pagina` (documento novo com outra
folha de rosto) ou `unidade_tematica` (célula mesclada cortada diferente). Nos
dois casos o conserto é no extrator, com o teste como juiz.

## Passo 9 — Voltar ao gate aberto

O catálogo novo **não** é fonte de geração até a conferência humana. O caminho de
volta é o do dia a dia:

1. Revisão das linhas com o roteiro:
   [`roteiro-conferencia-catalogo.md`](roteiro-conferencia-catalogo.md) e o
   `.docx` imprimível.
2. Conferência literal (`catalogo-conferir`) e aprovação com
   `catalogo-conferir --aprovar --responsavel "Prof. <nome>"` — passos 8 e 9 do
   roteiro, seguidos da montagem de teste.
3. Registro final em [`validacoes.md`](validacoes.md): data, quem conferiu, o que
   mudou no documento oficial, quantas linhas divergiram e o resultado da
   montagem de teste.

## Resumo em uma tela

```bash
# 1-2. baixar e comparar
md5sum /tmp/crmg_novo.pdf && sha256sum /tmp/crmg_novo.pdf   # vs meta.pdf_md5/pdf_sha256

# 3. conteúdo igual: copiar, atualizar data_acesso, regerar docx, registrar
# 4-6. conteúdo novo: copiar o PDF, reextrair, conferir contagens no PDF, gravar o catálogo

# 7. atualizar contagens de teste, roteiro, CSV e docx
python3 -m src.historia_gen conferencia-docx

# 8. portão
python3 -m src.historia_gen catalogo-validar
python3 -m pytest -q tests/test_historia_gen_catalogo.py

# 9. revisão (roteiro) + catalogo-conferir → --aprovar --responsavel → revalidar tudo
```

Nada aqui usa rede além do download do PDF, e nada tem custo de API.
