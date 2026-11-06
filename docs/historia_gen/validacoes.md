# Validações — Agente Gerador de Atividades de História (Fases 0 e 1)

Documento vivo de validações do design [aprovado](../designs/agente-atividades-historia-design.md) (2026-11-01). Registra o resultado e a data de cada Open Question e das medições das Fases 4 e 5. É pré-condição para qualquer ampliação de escopo.

**Status da Fase 0 (2026-11-01):** Q2 ✓ · Q3 ✓ · Q4 parcial (EM condicionado; EJA sem fonte) · Q1 pendente do professor · Q5 pendente do professor. **Fase 1 liberada** (pré-condições Q2 e Q3 fechadas).

**Status da Fase 1 (2026-11-02):** extração concluída — 97 habilidades de História dos Anos Finais (6º: 19 · 7º: 17 · 8º: 27 · 9º: 34) em `src/historia_gen/catalogo/dados/catalogo_crmg_ef_anos_finais.json`, com página impressa de origem por habilidade e tipo de modificação (legenda do próprio documento: só `original` e `X`). **Revisão registrada em 2026-11-03** (`revisao_aprovada: true`): a conferência literal automática (`catalogo-conferir`, que relê a camada de texto do PDF e confronta código, descrição, unidade, objeto e página das 97 linhas) passou sem divergência, e o `meta` registra `revisado_por`, `revisao_metodo` e `revisao_data`. O **visto do professor** por amostragem com o roteiro impresso segue pendente — não bloqueia a geração, que é ancorada no código. Duas anomalias do próprio documento estão registradas em [`src/historia_gen/catalogo/fonte_oficial.md`](../src/historia_gen/catalogo/fonte_oficial.md) (unidade quebrada no 7º ano; ano variável no nome da unidade do 9º ano). Roteiro da conferência em [`roteiro-conferencia-catalogo.md`](roteiro-conferencia-catalogo.md), com a lista das 97 linhas para marcar em [`conferencia_catalogo.csv`](conferencia_catalogo.csv) e a versão imprimível em [`roteiro-conferencia-catalogo.docx`](roteiro-conferencia-catalogo.docx) (roteiro em retrato + lista em paisagem, com coluna `OK` e espaço para a divergência; gerado por `python3 -m src.historia_gen conferencia-docx`).

**Status das Fases 2 e 3 (2026-11-02):** verificador e montagem implementados e verificados — consulta exata por (código, ano), recusa da folha inteira com um código fora do catálogo, recusa de entrada de outro ano ou sem confirmação do professor, montagem `.docx` nos dois modos (Arial, justificado, sem cabeçalho, rascunho no rodapé, gabarito separado) e log `registros.jsonl`. Gates: 46 testes do pacote verdes, `ruff check`/`ruff format --check` limpos e `mypy src/historia_gen` limpo. O extrator foi corrigido para gravar a página **impressa** e filtrar o escopo Anos Finais — sobre o PDF versionado ele reproduz o catálogo linha a linha, coberto por teste. **A geração real está liberada desde 2026-11-03**: o catálogo versionado passou na conferência literal e a montagem do exemplo roda sem `--catalogo` alternativo (folha + gabarito + log). Os testes de ponta a ponta que precisam de um catálogo diferente continuam usando a cópia de fixture.

## Q2 — Versão vigente do documento oficial ✓ RESOLVIDA (2026-11-01)

* **Página institucional oficial:** Portal Pedagógico/Escola de Formação da SEE-MG — <https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/curriculo-referencia-de-minas-gerais>
* **PDF oficial ("Versão atualizada"):** <https://portalpedagogico.educacao.mg.gov.br/wp-content/uploads/2026/05/CRMG-Infantil-e-Ensino-Fundamental-_Versao-atualizada.pdf>
* **Verificação por hash:** o PDF baixado do site em 2026-11-01 tem MD5 `123289db779177aa9e1c75fcd5182aed` e 8.968.394 bytes — **idênticos** aos da cópia do Drive registrada no `drive-audit/inventory.csv` (arquivos de 2026-03-01/02). A cópia do Drive **é** a versão vigente publicada no site.
* **Metadados do documento:** gerado em Word (Microsoft 365), CreationDate 2023-05-19 — o site republicou em 2026/05 o mesmo conteúdo; nenhuma atualização de conteúdo desde então.
* **Hashes de referência (para `MetaCatalogo`):**
  * `pdf_md5`: `123289db779177aa9e1c75fcd5182aed` (proveniência Drive/inventário)
  * `pdf_sha256`: `792857369c0c80dd87fff092137053e7a5cbed1c61fcbbd6caa6efbc072154ea`
* **Cópia no repositório:** `src/historia_gen/catalogo/dados/fonte_oficial/crmg_infantil_ef.pdf` (verificada por MD5 após a cópia).
* **Reconfirmação anual:** repetir este teste (baixar do site + comparar hash) no início de cada ano letivo; atualizar esta seção com data e resultado. Procedimento completo (do download ao teste de reprodução) em [`reextracao-anual.md`](reextracao-anual.md).

## Q3 — Camada de texto do PDF ✓ RESOLVIDA (2026-11-01)

O PDF **tem camada de texto** (PDF 1.7, tagged; `pdftotext` extrai com fidelidade as primeiras páginas). Decisão D2 confirmada: catálogo montado por **extração assistida** (`pdfplumber`, extra `dev`, import preguiçoso), com revisão manual obrigatória; `catalogo-extrair` deixa de ser condicional.

**Notas de extração para a Fase 1:**

* A seção de **História — Anos Finais** é a **seção 15** do documento: sumário na p. 547 (impressa), competências específicas p. 548, diretrizes p. 550, **Organizador Curricular p. 558**.
* A numeração impressa difere da física do PDF (há folha de rosto e equipe técnica antes) — a extração precisa mapear página física → página impressa e registrar **a impressa** no campo `pagina` do catálogo.
* Contagem esperada de habilidades por ano: a preencher na Fase 1, a partir do Organizador Curricular, e a registrar aqui como contraprova do catálogo.

## Q4 — Documentos oficiais de EM e EJA ◑ PARCIAL (2026-11-01)

* **Ensino Médio:** existe documento oficial — "Currículo Referência de Minas Gerais (Ensino Médio)", homologado em abril de 2021, disponível em espelho do MEC (<https://www.gov.br/mec/pt-br/novo-ensino-medio-descontinuado/pdfs/RCSEEMG.pdf>); a seção correspondente do Portal Pedagógico aparece como "em desenvolvimento", sem "versão atualizada" equivalente à de Infantil/Fundamental. **Conclusão: EM permanece condicionado** — a entrar só depois de confirmar no site da SEE-MG qual é a fonte canônica vigente (URL + versão + hash), pelo mesmo processo da Q2.
* **EJA:** não foi localizado documento exclusivo de currículo referência para EJA; a etapa é regulada por **resoluções de matriz curricular** (Resolução SEE nº 4.798/2022 — alterações na matriz EJA 2023; Resolução SEE nº 4.668/2021 — matrizes do Ensino Médio), que são outro tipo de documento, não um organizador de habilidades por componente. **Conclusão: EJA permanece fora** até existir (ou ser confirmado) documento oficial equivalente.
* Referências consultadas: [Portal Pedagógico — Estrutura Curricular](https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino), [Movimento pela Base — referencial do Novo Ensino Médio de MG homologado](https://observatorio.movimentopelabase.org.br/novo-ensino-medio-referencial-curricular-de-minas-gerais-e-homologado), [MEC — RCSEEMG.pdf](https://www.gov.br/mec/pt-br/novo-ensino-medio-descontinuado/pdfs/RCSEEMG.pdf).

## Q1 — Autoria do material de suporte 3 ⏳ PENDENTE (professor)

Conversar com a escola/AEE sobre quem produz a atividade de suporte 3 hoje. Não bloqueia nenhuma fase da v1; decide se suporte 3 volta à pauta. Resultado: _a registrar_.

## Q5 — Linha de base de adaptação manual ◑ INSTRUMENTO PRONTO, NÚMERO PENDENTE

O número é humano — cronometrar 1–2 adaptações reais feitas **sem** o pipeline
continua sendo trabalho do professor; o instrumento não substitui a medição e se
recusa a falar em ganho sem ela:

* formulário impresso: `python3 -m src.historia_gen tempo-formulario` gera [`q5-formulario.docx`](q5-formulario.docx) — uma página por medição (padrão 2 vias), com as etapas do protocolo, o total em destaque, o retrabalho e o comando de registro; conferido em impressão (LibreOffice + pymupdf): 1 página por via, última linha a 26,6 cm do topo (1,1 cm do limite inferior da área útil), sem cabeçalho;
* registro: `python3 -m src.historia_gen tempo-manual --tema "Roma Antiga" --ano "6º ano EF" --minutos 65 --quem "Prof. …"` grava em [`q5-linha-de-base.csv`](q5-linha-de-base.csv);
* comparação: `python3 -m src.historia_gen tempo-manual --comparar` confronta a mediana manual com a mediana de `duracao_s` do `registros.jsonl`; CSV vazio ou log sem medida ⇒ recusa (exit 1) e nenhuma afirmação de ganho;
* protocolo e o que cronometrar: [`q5-linha-de-base.md`](q5-linha-de-base.md).

Resultado: _a registrar_ (ex.: "Roma Antiga, 6º ano, suporte 2 — XX min em AAAA-MM-DD").

## Fase 4 — Comparação com atividades reais ◑ EM ANDAMENTO (2026-11-02)

Gerar os mesmos temas de 3–5 atividades adaptadas à mão (inventário: `drive-audit/inventory.csv`) e comparar lado a lado.

**1º par comparado** — 8º ano, Revolução Industrial: avaliação adaptada à mão do Drive (`2026_HIST_8ANO_AVALIAÇÃO_ADAPTADA_2TRIMESTRE_CAIC.docx`, 2026-08-15, 10 questões, 7 páginas, 8 imagens) contra folha adaptada gerada pelo pipeline (`EF08HI03X`, p. 570, 10 questões, 1 página).

**2º par comparado** — 9º ano, Descolonização da África e da Ásia: caderno adaptado de suporte 3 (`Atividade_Adaptada_Descolonizacao_Suporte3.docx`, 5 tarefas, 11 páginas, registro de desempenho, código declarado “não verificado”) contra folha gerada pelo pipeline (`EF09HI31X`, p. 577, 10 questões, 1 página, 8 citações de fonte). O par confirmou a maior lacuna da v1 (registro de mediação) e expôs um defeito de contrato: `nivel_suporte: 3` era aceito sem aviso e a folha saía rotulada com um nível que a v1 não implementa — agora a entrada é recusada.

**3º par comparado** — 6º ano, Roma Antiga: atividade **regular** do professor (`3pprhistoria6ano.docx`, 41.314 bytes, MD5 `09fee60c…`, 13 questões em 3 páginas, 7 de múltipla escolha sem espaço de marcação, sem código de habilidade e sem gabarito) contra folha regular gerada (`EF06HI11X`, p. 566, 10 questões — 2 marcar, 2 V/F, 3 completar, 3 ligar — em 2 páginas, 9 citações de fonte, gabarito separado). Primeiro par com folha de atividade regular dos dois lados; confirmou o G1 (nenhum dos quatro baselines tem código com página), enfraqueceu o GAP-5 (essa peça não usa identificação) e mostrou que a citação por item é o que ocupa a segunda página. A entrada foi recusada na primeira tentativa pelo próprio validador (dois itens de completar com o mesmo banco de palavras) — a checagem funcionou como devia.

**4º par comparado** — 7º ano, Grandes Navegações e Reforma: avaliação adaptada do Drive (`2026_HIST_7ANO_AVALIAÇÃO_ADAPTADAS_2TRIMESTRE_CORACI.docx`, Google Doc id `1b_H2ve…`, exportado em 2026-11-04, 5 páginas, 8 imagens, 10 números mas 11 itens — o 06 aparece duas vezes —, três habilidades misturadas e identificação com Nome/Data/Valor/Nota, sem registro e sem gabarito) contra folha adaptada gerada (`EF07HI05X`, p. 568, 10 questões em 3 páginas — 2 do estudante + professor — com ficha de planejamento e caixa de vocabulário). O par confirma GAP-2 e GAP-5 no 7º ano e o G1 (três códigos sem página contra um código ancorado), e registra uma pendência de redação: a folha gerada escreve 16,7 palavras por frase contra 9,9 do baseline — “frases curtas” ainda não está cumprido nesta peça.

Medidas, lacunas (GAP-1 a GAP-7) e ganhos (G1 a G5) dos quatro pares em [`fase-4-comparativo.md`](fase-4-comparativo.md). Tempo de montagem medido: 0,18 a 0,19 s por folha (determinístico, sem rede).

**Primeira mudança de v1.1 saída da Fase 4 (2026-11-02, template 1.1):** página final de uso do professor com `registro_mediacao: true` — como aplicar (orientações geradas da folha + `orientacoes_aplicacao` do professor), grade por item com sozinho / apoio parcial / apoio total, data, tempo e observações, marcada como página que não vai para o estudante. O nível de suporte diferente de 2 passou a ser recusado na entrada, em vez de gerar folha com rótulo falso.

**Segunda mudança de v1.1 (2026-11-02, template 1.2), GAP-1/GAP-4:** itens de **marcar/pintar** (`itens_marcar`: comando, frase opcional, 2–4 opções com espaço `( )`, `correta` obrigatoriamente entre elas) e de **verdadeiro/falso** (`itens_vf`: afirmação + marcação Verdadeiro/Falso, com `correcao` obrigatória quando falsa) entram na folha depois da leitura e antes dos itens de escrever; o gabarito traz a opção certa e, na afirmação falsa, o que é correto. Validação de entrada cobre opções repetidas, `correta` fora das opções, afirmação falsa sem correção e itens duplicados (marcar, V/F, completar e ligar) — recusa já como lista de reprovações, não como exceção na gravação. Ainda faltavam do comparativo: figura de apoio, parear iguais, caça-palavras e ordenação.

**Terceira mudança de v1.1 (2026-11-03, template 1.3), GAP-1/GAP-4:** itens de
**parear iguais** (`itens_parear`: 2–6 palavras, as mesmas nas duas colunas em
ordens diferentes — a resposta é um traço, sem escrita nem leitura nova),
**ordenação** (`itens_ordenar`: itens entram na ordem correta, saem embaralhados
para numerar e o gabarito imprime a sequência) e **figura de apoio** (`figuras`:
PNG/JPEG local, 14 cm centralizada, legenda e citação) — esta última com recusa
de imagem ausente ou em formato não aceito e caminho relativo resolvido a partir
da pasta do `atividade.json`. A grade do professor passou a listar **todos** os
itens impressos (antes os itens de marcar e V/F da 1.2 não entravam na grade) e o
log registra a contagem por formato. O **caça-palavras** fica fora: o design
aprovado já o rejeitou como escopo da v1 (Alternativa F — layout difícil de
automatizar bem em `.docx`, com geradores gratuitos disponíveis). Gates: 72
testes do pacote verdes, `ruff check`/`ruff format --check` e
`mypy src/historia_gen` limpos; o exemplo versionado passou a exercitar parear e
ordenação (13 questões).

**Quarta mudança de v1.1 (2026-11-03, template 1.4), gate e impressão da figura:**
o gate `revisao_aprovada` foi aberto pelo caminho verificável, não por edição
manual do JSON: `catalogo-conferir` relê a camada de texto do PDF e confronta as
97 linhas (código, descrição, unidade, objeto e página); só sem divergência
`--aprovar --responsavel` grava `revisao_aprovada`, `revisado_por`,
`revisao_metodo` e `revisao_data` no `meta`, e a aprovação é recusada se houver
divergência. A **figura** ganhou teto de altura (17 cm) além da largura de 14 cm:
uma imagem retrato de 14 cm de largura não cabe na área útil do A4 com legenda e
citação e sairia cortada no pé da página. A medida foi feita em impressão real —
`scripts/verificar_impressao_figura.py` gera figuras larga (1600×900), quadrada
(1000×1000) e retrato (700×1400), converte no LibreOffice e mede o retângulo no
PDF: 14,00 × 7,88 cm, 14,00 × 14,00 cm e 8,50 × 17,00 cm, as três centralizadas
(10,50 cm), dentro das margens e com legenda e citação na mesma página. O log
passou a registrar `duracao_s` da montagem, e o subcomando `tempo-manual` guarda
a medição humana da Q5 e compara medianas sem inventar linha de base. Gates: 86
testes do pacote verdes, `ruff check`/`ruff format --check` e
`mypy src/historia_gen` limpos.

**Quinta mudança de v1.1 (2026-11-03, template 1.6), impressão com figura real:**
a folha de Roma Antiga (6º ano, `EF06HI11X`, p. 566) foi montada com um **mapa
real** do Império em 117 d.C. (ArdadN, Wikimedia Commons, domínio público,
rótulos em português), convertida no LibreOffice e revisada página a página no
PDF. A figura sai a 14,00 × 10,19 cm, centralizada (10,50 cm), com legenda e
citação na mesma página — a conferência anterior, feita com PNG 1×1, não
mostrava nada disso. A revisão achou um defeito de paginação: a grade do
registro chegava ao pé da folha e o campo de observações caía sozinho numa
quinta página 95% vazia. Correções: coluna do item de 7,8 para 8,6 cm (as três
de marcação a 2,7/2,8/2,7 cm), rótulo do item resumido em 46 caracteres em vez
de 70, respiro de 4 pt na lista "Como aplicar", rótulo de observações colado na
caixa e linha de data/tempo com 1,0 cm de altura. O registro do professor passou
a fechar em **uma página** (termina a 23,0 cm dos 25,7 cm úteis, com 4,7 cm de
folga para a quebra de linha do Word) e a folha ficou em **3 páginas** — a
terceira traz só a tabela do ligar, porque o bloco instrução + grade + fontes não
quebra entre páginas, e esse é o piso de paginação com os formatos atuais.
Artefatos da revisão (`.docx`, `.pdf` e páginas em PNG) em
`saida/roma-antiga-figura/pdf/`. Gates: 88 testes do pacote verdes, `ruff
check`/`ruff format --check` e `mypy src/historia_gen` limpos.

**Sexta mudança de v1.1 (2026-11-03, template 1.7), GAP-7 — uma tarefa por página:**
o suporte 3 deixou de ser apenas um rótulo barrado: `nivel_suporte: 3` no modo
adaptado monta **uma tarefa por página**. Cada bloco de leitura e cada item
abrem página nova, e a página repete instrução, banco de palavras e linha de
fontes — a anterior já foi recolhida, então a página precisa se resolver sozinha.
Medido na folha da Descolonização (2 blocos + 4 itens de completar + 1 tabela de
ligar): **8 páginas** (7 tarefas + a página do professor), contra 1 página do
mesmo conteúdo em suporte 2. A revisão de impressão achou um defeito nessa
primeira versão — a linha "Fontes:" encostava na borda da grade, porque o
respiro só existia na folha contínua — e ele foi corrigido. **O suporte 2 não
mudou**: o `.docx` gerado antes e depois da refatoração tem os mesmos
parágrafos, as mesmas tabelas (dimensões e células) e as mesmas quebras de
página; a única diferença é a ordem sorteada, porque a semente é aleatória a
cada `montar`. O nível 1 segue recusado e o nível 3 no modo regular também (é o
defeito de contrato do par 2 voltando com outro nome). Gates: 96 testes do
pacote verdes, `ruff check`/`ruff format --check` e `mypy src/historia_gen`
limpos.

**Sétima mudança de v1.1 (2026-11-04, template 1.8), GAP-2 residual — ficha de
planejamento:** o caderno de referência adaptado à mão abre com **objetivo,
duração, metodologia, recursos e público/PDI**; a página do professor imprimia o
registro da mediação e o "como aplicar", mas não essa ficha. O campo opcional
`planejamento` passou a imprimir a ficha no topo da página do professor, num
bloco único (uma linha por campo empurrava a caixa de observações para uma
página quase vazia — visto na primeira medição). A entrada recusa `planejamento`
sem `registro_mediacao: true`, em vez de aceitar um campo que não seria impresso,
e recusa ficha sem nenhum campo preenchido. Medido em impressão real no exemplo
versionado (13 itens, 11 pt): a folha do professor volta a fechar em **uma
página**, terminando a 27,1 cm dos 27,7 cm úteis; para isso a caixa de
observações cede 1,4 cm (de 3,0 para 1,6 cm, três linhas de escrita à mão). O
suporte 2 e o suporte 3 sem ficha não mudaram. Revisada também em duas folhas
adaptadas reais: suporte 3 da Descolonização (8 páginas, página do professor
terminando a 22,9 cm) e suporte 2 da mesma atividade (2 páginas, professor a
22,3 cm). Gates: 100 testes do pacote verdes, `ruff check`/`ruff format --check`
e `mypy src/historia_gen` limpos.

**Oitava mudança de v1.1 (2026-11-04, template 1.9), GAP-6 — caixa de
vocabulário:** o caderno de referência adaptado à mão abre com poucas
palavras-chave que percorrem todas as tarefas; a folha gerada só tinha banco de
palavras nos itens de completar, e o banco mistura respostas e distratores —
não serve como vocabulário. Entrou o campo opcional `vocabulario` (até 8
palavras, sem repetição, conferidas sem distinguir maiúsculas), impresso numa
caixa de uma linha com o rótulo em negrito no topo da folha. No suporte 3 a
caixa volta no topo de **cada** tarefa, ao lado do banco de palavras: a página
anterior já foi recolhida e precisa se resolver sozinha. Medição: no exemplo
de 13 itens com ficha e vocabulário a primeira página termina a 26,3 cm dos
27,7 cm úteis e a folha continua em **3 páginas**; no suporte 3 a caixa custa
0,5 cm por página e a folha segue em **8 páginas**, com a página do professor
inalterada (22,9 cm). O par 1 (regular) não usava glossário: sem `vocabulario`
nada muda. Gates: 103 testes do pacote verdes, `ruff check`/`ruff format
--check` e `mypy src/historia_gen` limpos.

**Pendências:** mais 1–2 pares (de preferência de outra escola ou disciplina, para variar o formato de mão) e a linha de base de tempo manual da Q5 — sem ela não há como afirmar ganho de tempo.

## Fase 5 — Medição em semana real de aulas _a realizar_

Tempo do fluxo (redação + montagem + revisão) contra a linha de base (Q5) + aceitação sem retrabalho em ≥ 4/5 atividades (critério do G7). Resultado: _a registrar_.
