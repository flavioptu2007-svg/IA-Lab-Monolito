# Roteiro de conferência do catálogo CRMG — aprovação das 97 habilidades

Guia para a revisão que libera (e mantém) o catálogo como fonte de geração. O
catálogo versionado está com `revisao_aprovada: true` desde 2026-11-03, depois da
conferência literal automática (97/97 linhas) contra o PDF; o que resta é o
**visto do professor** por amostragem. Sem revisão registrada, o subcomando
`montar` recusa qualquer folha — e é esta conferência que abre o gate.

**Quem faz:** professor(a) de História dos Anos Finais.
**O que se confere:** que o catálogo transcreve **literalmente** o documento
oficial. Não é revisão pedagógica das habilidades nem julgamento do currículo —
é controle de fidelidade da transcrição.
**Tempo estimado:** 40–60 min (13 páginas do organizador, 97 linhas).
**Decisão ao final:** aprovar (gate aberto) ou devolver divergências.

---

## 1. Antes de começar

| Item | Caminho |
|---|---|
| Documento oficial (PDF versionado) | `src/historia_gen/catalogo/dados/fonte_oficial/crmg_infantil_ef.pdf` |
| Catálogo a conferir | `src/historia_gen/catalogo/dados/catalogo_crmg_ef_anos_finais.json` |
| Lista de conferência (uma linha por habilidade) | [`conferencia_catalogo.csv`](conferencia_catalogo.csv) |
| **Roteiro + lista em um único `.docx` imprimível** | [`roteiro-conferencia-catalogo.docx`](roteiro-conferencia-catalogo.docx) |
| Registro das anomalias do próprio documento | [`src/historia_gen/catalogo/fonte_oficial.md`](../../src/historia_gen/catalogo/fonte_oficial.md) |

Para imprimir, use o `.docx` pronto: ele traz este roteiro em retrato e a lista
das 97 habilidades em paisagem, com coluna `OK` para marcar e espaço para
escrever a divergência — não é preciso imprimir o CSV junto. O CSV continua
servindo para marcar na tela.

Checagem de integridade (deve passar antes de começar; confirma que o PDF é o
mesmo de onde o catálogo foi extraído):

```bash
python3 -m src.historia_gen catalogo-validar
```

Esperado: `integridade: MD5 e SHA-256 conferem com o PDF versionado`, as quatro
contagens (`6º: 19 · 7º: 17 · 8º: 27 · 9º: 34`) e o aviso `revisão manual
PENDENTE`. Se a integridade falhar, **pare**: o PDF não é o da extração.

Abrir o PDF no leitor de páginas e a planilha do CSV lado a lado. O CSV já vem
ordenado por página impressa, então a conferência anda página por página.

## 2. Como navegar no PDF

* O organizador de História começa na **página impressa 558**; as habilidades
  dos Anos Finais ocupam as impressas **565 a 577**.
* A página **física** do PDF é sempre a **impressa + 1** (há folha de rosto e
  equipe técnica antes). Para ver a página impressa 566, vá para a física 567 —
  o número impresso aparece no **topo** da página.
* A tabela tem 4 colunas: **ANO | Unidades Temáticas | Objetos de Conhecimento |
  Habilidades**. As duas colunas do meio vêm de células mescladas: valem para
  todas as linhas do bloco.

## 3. O que conferir em cada uma das 97 linhas

Para cada habilidade do CSV, comparar com a linha correspondente do PDF:

1. **Código** — idêntico ao impresso, incluindo o sufixo (`X`, `MG`, `A/B/C`,
   `P1/P2`). Um sufixo perdido muda o significado (a legenda está em
   `fonte_oficial.md`).
2. **Descrição** — idêntica, palavra por palavra, sem cortes nem "melhorias".
   Erros de digitação do próprio CRMG também são transcritos como estão.
3. **Ano** — a linha em que a habilidade aparece (`6º ano EF` … `9º ano EF`).
4. **Unidade temática e objeto de conhecimento** — os do bloco em que a linha
   está, mesmo quando repetidos em várias habilidades.
5. **Página** — o número impresso no topo da página de onde a linha foi tirada.

Tipos possíveis de `tipo_modificacao` no CSV: `original` (43 habilidades) e
`alterada` (54) — só esses dois ocorrem em História/Anos Finais.

## 4. Lote por página

Confira uma página por vez. A tabela abaixo é a distribuição real do catálogo;
usar a coluna de códigos como lista de checagem evita pular linha.

| Página impressa | Física | Habilidades | Anos | Códigos |
|---|---|---|---|---|
| 565 | 566 | 1 | 6º | EF06HI01X |
| 566 | 567 | 10 | 6º | EF06HI02X, EF06HI03X, EF06HI04X, EF06HI05, EF06HI06X, EF06HI07X, EF06HI08, EF06HI09, EF06HI10X, EF06HI11X |
| 567 | 568 | 7 | 6º | EF06HI12X, EF06HI13, EF06HI14, EF06HI15, EF06HI16X, EF06HI17X, EF06HI18X |
| 568 | 569 | 8 | 6º, 7º | EF06HI19X, EF07HI01, EF07HI02, EF07HI03X, EF07HI04, EF07HI05X, EF07HI06X, EF07HI07 |
| 569 | 570 | 6 | 7º | EF07HI08X, EF07HI09X, EF07HI10, EF07HI11X, EF07HI12X, EF07HI13X |
| 570 | 571 | 10 | 7º, 8º | EF07HI14X, EF07HI15, EF07HI16X, EF07HI17X, EF08HI01X, EF08HI02X, EF08HI03X, EF08HI04X, EF08HI05X, EF08HI06 |
| 571 | 572 | 10 | 8º | EF08HI07, EF08HI08, EF08HI09, EF08HI10X, EF08HI11, EF08HI12, EF08HI13, EF08HI14X, EF08HI15X, EF08HI16 |
| 572 | 573 | 6 | 8º | EF08HI17X, EF08HI18X, EF08HI19X, EF08HI20X, EF08HI21, EF08HI22 |
| 573 | 574 | 6 | 8º, 9º | EF08HI23, EF08HI24, EF08HI25, EF08HI26, EF08HI27X, EF09HI01X |
| 574 | 575 | 7 | 9º | EF09HI02, EF09HI03X, EF09HI04X, EF09HI05, EF09HI06, EF09HI07X, EF09HI08X |
| 575 | 576 | 9 | 9º | EF09HI09X, EF09HI10, EF09HI11, EF09HI12X, EF09HI13X, EF09HI14, EF09HI15, EF09HI16X, EF09HI17 |
| 576 | 577 | 7 | 9º | EF09HI18, EF09HI19, EF09HI20X, EF09HI21X, EF09HI22, EF09HI23X, EF09HI24 |
| 577 | 578 | 10 | 9º | EF09HI25X, EF09HI26X, EF09HI27, EF09HI28, EF09HI29, EF09HI30X, EF09HI31X, EF09HI32, EF09HI33X, EF09HI34 |

## 5. Anomalias já conhecidas — decisão esperada

Estas duas linhas **parecem** erro, mas são transcrição fiel. Não corrija o
texto: confirme que o catálogo reproduz o que o documento imprime.

1. **7º ano — unidade quebrada (p. 568).** `EF07HI01` e `EF07HI03X` registram o
   fragmento `moderno e a conexão entre sociedades africanas, americanas e
   europeias`, porque a unidade aparece partida entre duas linhas do organizador.
   Decisão esperada: manter o literal (é o que o aluno vê no documento oficial).
2. **9º ano — ano variável no nome da unidade (pp. 575–577).** A unidade
   "Modernização, ditadura civil-militar e redemocratização: o Brasil após …"
   varia o ano a cada linha (1946, 1947, 1948, 1949, 1951, 1953, 1954, 1955).
   Decisão esperada: manter o que cada linha imprime.

Se a decisão for outra (por exemplo, corrigir a unidade quebrada), isso é uma
**mudança de regra** do catálogo: registrar por escrito e tratar como alteração
do extrator, não como edição manual do JSON.

## 6. Registrando o resultado

No CSV, por linha:

* `conferido` — `OK` quando os cinco itens do passo 3 conferem.
* `observacao` — só quando houver divergência: o que está impresso no PDF e o
  que está no catálogo (ex.: "PDF imprime EF06HI07; catálogo tem EF06HI07X").

Ao final, o CSV deve ter **97 linhas com `OK`** para a aprovação.

## 7. Se encontrar divergência

**Não edite o JSON à mão.** O catálogo é gerado pelo extrator; corrigir só o
arquivo faria a próxima extração desfazer a correção sem aviso. O conserto é:

1. registrar a divergência no CSV (página, código, texto impresso);
2. corrigir a leitura em `src/historia_gen/catalogo/extraidor.py`;
3. regerar e conferir que a extração continua reproduzindo o catálogo:

```bash
python3 src/historia_gen/catalogo/extraidor.py     # regrava o JSON
python3 -m src.historia_gen catalogo-validar       # integridade + contagens
python3 -m pytest -q tests/test_historia_gen_catalogo.py
```

4. repetir a conferência apenas das linhas afetadas.

O extrator falha de propósito quando o número de códigos encontrados no texto do
PDF não bate com as células extraídas — se ele rodar limpo sobre o PDF
versionado, a divergência era de transcrição, não de extração.

## 8. Aprovando o catálogo

Com 97 linhas `OK`:

1. Rodar a conferência literal contra o PDF — ela relê a camada de texto e
   compara código, descrição, unidade, objeto e página das 97 linhas:

   ```bash
   python3 -m src.historia_gen catalogo-conferir
   ```

2. Com a conferência limpa, registrar a aprovação (o comando se recusa a aprovar
   com divergência; o nome fica em `meta.revisado_por`, junto do método e da
   data):

   ```bash
   python3 -m src.historia_gen catalogo-conferir --aprovar --responsavel "Prof. <nome completo>"
   ```

3. Conferir que `catalogo-validar` mostrou `revisão: aprovada …`. O teste do
   gate, em `tests/test_historia_gen_cli.py` →
   `test_catalogo_versionado_existe_no_repositorio`, exige
   `revisao_aprovada is True` com `revisado_por` e `revisao_metodo` preenchidos.

4. Revalidar tudo:

```bash
python3 -m src.historia_gen catalogo-validar   # sem o aviso de revisão pendente
python3 -m pytest -q tests/test_historia_gen_*.py
python3 -m src.historia_gen montar src/historia_gen/exemplos/atividade-exemplo.json --saida /tmp/roma
```

O último comando é o que antes era impossível: montar com o catálogo versionado,
sem `--catalogo` alternativo.

5. Registrar no [`validacoes.md`](validacoes.md) (Fase 1): data, quem conferiu,
   quantas linhas, divergências encontradas e o resultado da montagem de teste.

## 9. Critério de conclusão

- [ ] `catalogo-validar` passou antes da conferência (integridade + contagens).
- [ ] 97/97 linhas do CSV com `OK`.
- [ ] As duas anomalias conhecidas decididas e registradas.
- [ ] `meta.revisao_aprovada: true`, com `revisado_por` e `revisao_metodo` preenchidos.
- [ ] Teste do gate (`revisao_aprovada is True`) e `validacoes.md` atualizados.
- [ ] `pytest` verde e `montar` com o catálogo versionado gerando folha + gabarito.
- [ ] `validacoes.md` atualizado.

## Regenerando o `.docx` imprimível

O `.docx` também é derivado do catálogo — código de geração em
`src/historia_gen/conferencia.py`, comando:

```bash
python3 -m src.historia_gen conferencia-docx
```

Ele não exige `revisao_aprovada: true` (é ferramenta de revisão, não de
geração de folha). O teste `test_docx_de_conferencia_esta_atualizado`
(`tests/test_historia_gen_catalogo.py`) regenera em memória e compara texto e
células com o arquivo versionado: se o catálogo ou o roteiro mudarem sem o
arquivo ser regerado, o build quebra.

## Regenerando o CSV de conferência

O CSV é derivado do catálogo — se o catálogo mudar (nova extração anual), gerar
de novo para não conferir uma lista velha:

```bash
python3 - <<'PY'
import csv, json
d = json.load(open("src/historia_gen/catalogo/dados/catalogo_crmg_ef_anos_finais.json"))
habs = sorted(d["habilidades"], key=lambda h: (h["pagina"], h["codigo"]))
with open("docs/historia_gen/conferencia_catalogo.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["pagina_impressa", "ano", "codigo", "tipo_modificacao",
                "unidade_tematica", "objeto_conhecimento", "descricao",
                "conferido", "observacao"])
    for h in habs:
        w.writerow([h["pagina"], h["ano"], h["codigo"], h["tipo_modificacao"],
                    h["unidade_tematica"], h["objeto_conhecimento"], h["descricao"], "", ""])
PY
```

Ao regerar, a marcação de conferência anterior é perdida (colunas `conferido` e
`observacao` voltam vazias) — por isso a conferência completa só se repete
quando o documento oficial muda.

O teste `test_csv_de_conferencia_acompanha_o_catalogo`
(`tests/test_historia_gen_catalogo.py`) compara o CSV com o catálogo linha a
linha e falha se um deles mudar sem o outro — a lista de conferência não
consegue ficar velha em silêncio.
