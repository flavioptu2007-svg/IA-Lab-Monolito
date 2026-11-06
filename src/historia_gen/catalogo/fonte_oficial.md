# Fonte oficial do catálogo curricular — CRMG (SEE-MG)

Registro de proveniência da fonte de códigos do projeto. Atualizar **uma vez por ano**, no início de cada ano letivo — processo completo, do download do PDF ao teste de reprodução, em [`docs/historia_gen/reextracao-anual.md`](../../../docs/historia_gen/reextracao-anual.md). Ver também [`docs/historia_gen/validacoes.md`](../../../docs/historia_gen/validacoes.md).

## Identificação da fonte

* **Documento:** Currículo Referência de Minas Gerais — Educação Infantil e Ensino Fundamental
* **Página institucional:** <https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/curriculo-referencia-de-minas-gerais>
* **PDF oficial ("Versão atualizada"):** <https://portalpedagogico.educacao.mg.gov.br/wp-content/uploads/2026/05/CRMG-Infantil-e-Ensino-Fundamental-_Versao-atualizada.pdf>
* **Versão:** "Versão atualizada"; conteúdo do PDF gerado em 2023-05-19 (metadados do arquivo); site republicou em 2026/05 o mesmo conteúdo
* **Data de acesso/confirmação:** 2026-11-01
* **`pdf_md5`:** `123289db779177aa9e1c75fcd5182aed` — igual à cópia do Drive registrada no `drive-audit/inventory.csv`
* **`pdf_sha256`:** `792857369c0c80dd87fff092137053e7a5cbed1c61fcbbd6caa6efbc072154ea`
* **Cópia versionada no repositório:** `dados/fonte_oficial/crmg_infantil_ef.pdf` (8.968.394 bytes)

## Estrutura do documento usada na extração

* **Seção 15 — HISTÓRIA** (Anos Finais): páginas impressas 547–592; **Organizador Curricular** a partir da p. impressa 558.
* **Mapeamento de página:** página física do PDF = página impressa + 1 (o organizador vai das físicas 559 a 593; o 6º ano começa na física 566).
* **Tabela:** 4 colunas (ANO | Unidades Temáticas | Objetos de Conhecimento | Habilidades), com células mescladas verticalmente reconstruídas pela grade desenhada do PDF.
* **Ferramenta:** `pymupdf 1.28.2` (já presente no ambiente) — o design citava `pdfplumber`; desvio registrado, sem impacto (extração por grade real, validada por contagem).
* **Extração reproduzível:** `python3 src/historia_gen/catalogo/extraidor.py` — grava a **página impressa** (física − 1, conferida no número impresso no topo da página), filtra só o escopo Anos Finais (o organizador começa na física 566, ainda com o fim do 5º ano) e confronta o total de códigos do texto bruto com as células extraídas e as contagens registradas neste arquivo; qualquer divergência falha. Rodando sobre o PDF versionado, reproduz o catálogo linha a linha.

## Legenda de modificação de códigos (do próprio documento)

| Sufixo | Significado |
|---|---|
| *(nenhum)* | Habilidade original da BNCC |
| `X` | Alterada (modificada pelo CRMG dentro das possibilidades do MEC) |
| `MG` | Criada — não existia na BNCC |
| `A`, `B`, `C`… | Desmembrada |
| `P1`, `P2`… | Progressão (reestruturada ano a ano) |

Em História/Anos Finais ocorrem apenas códigos originais e alterados (`X`).

## Contagens esperadas (contraprova do catálogo)

| Ano | Habilidades |
|---|---|
| 6º ano EF | 19 |
| 7º ano EF | 17 |
| 8º ano EF | 27 |
| 9º ano EF | 34 |
| **Total** | **97** |

Testada por `tests/test_historia_gen_catalogo.py` (asserção de completeza).

## Anomalias encontradas no documento oficial (registradas, não herdadas como correção)

Transcrição **literal** é a regra do catálogo; o que o documento imprime é o que o catálogo registra. As duas anomalias abaixo ficam registradas aqui para a decisão da revisão manual:

1. **7º ano — unidade quebrada no organizador:** a unidade "O mundo moderno e a conexão entre sociedades africanas, americanas e europeias" aparece partida entre duas linhas da tabela; as células de `EF07HI01` e `EF07HI03X` registram o fragmento literal "moderno e a conexão entre sociedades africanas, americanas e europeias".
2. **9º ano — ano variável no nome da unidade:** "Modernização, ditadura civil-militar e redemocratização: o Brasil após …" repete-se por linha com o ano variando (1946, 1947, 1948, 1949, 1951, 1953, 1954, 1955) — provável cadeia de erratas no próprio CRMG. Cada habilidade registra o que a sua linha imprime.

## Status da revisão

* Extração: **concluída** (2026-11-02; 103 células no organizador, 97 do escopo Anos Finais, 0 avisos).
* Reprodução: coberta por `test_extrator_reproduz_o_catalogo_versionado` — reextrair o PDF versionado devolve o catálogo linha a linha. Procedimento anual em [`reextracao-anual.md`](../../../docs/historia_gen/reextracao-anual.md).
* **Revisão: registrada em 2026-11-03** — `revisao_aprovada: true`. A conferência literal automática (`python3 -m src.historia_gen catalogo-conferir`) relê a camada de texto do PDF e confronta as 97 linhas (código, descrição, unidade temática, objeto de conhecimento e página) sem divergência; o `meta` guarda `revisado_por`, `revisao_metodo` e `revisao_data`. O **visto do professor** (amostragem de páginas com o roteiro impresso) segue pendente e não bloqueia a geração — a cada reextração anual o `meta` volta a `false` e a conferência se repete.
