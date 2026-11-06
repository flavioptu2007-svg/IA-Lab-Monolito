# Fase 4 — Comparativo: atividade gerada × atividade adaptada à mão (Drive)

Comparativo da Fase 4 do design [aprovado](../designs/agente-atividades-historia-design.md):
o mesmo tema e a mesma série, uma atividade **gerada pelo pipeline** e uma
**adaptada à mão** pelo professor. O objetivo da fase não é eleger vencedor: é
listar, com o material real na mão, o que a v1 já cobre e o que ainda falta.

**Data:** 2026-11-02 (pares 1–3); 2026-11-04 (par 4). **Pares comparados:** 4
(a Fase 4 pede 3–5 — ver Limitações).

| Par | Série | Tema | Feita à mão (baseline) | Gerada pelo pipeline |
|---|---|---|---|---|
| 1 | 8º ano | Revolução Industrial | avaliação adaptada, 7 páginas, 8 imagens | `EF08HI03X` (p. 570), 10 questões, 1 página |
| 2 | 9º ano | Descolonização da África e da Ásia | caderno adaptado de suporte 3, 11 páginas, 5 tarefas | `EF09HI31X` (p. 577), 10 questões, 1 página |
| 3 | 6º ano | Roma Antiga | atividade regular, 13 questões, 3 páginas, sem gabarito | `EF06HI11X` (p. 566), 10 questões, 2 páginas |
| 4 | 7º ano | Grandes Navegações e Reforma | avaliação adaptada, 10 questões, 5 páginas, 8 imagens, 3 habilidades | `EF07HI05X` (p. 568), 10 questões, 3 páginas |

Os arquivos gerados estão em `saida/fase-4/` (não versionado), com o
`registros.jsonl` das duas gerações e as entradas `.json` correspondentes.

---

## 1. Par 1 — Revolução Industrial (8º ano)

### 1.1 Os dois documentos

| | Adaptada à mão (baseline) | Gerada pelo pipeline |
|---|---|---|
| Arquivo | `2026_HIST_8ANO_AVALIAÇÃO_ADAPTADA_2TRIMESTRE_CAIC.docx` | `revolucao-industrial-fabricas-cidades-e-trabalho.docx` |
| Origem | Drive do professor — id `1gybcFX-mWudbbP47zUTpEoZbgJPAGLLs`, 24.355.553 bytes, MD5 `c60ef02c446a9da9afd7de191233738e`, modificado em 2026-08-15 | `montar` + `finalizar` (log em `saida/fase-4/registros.jsonl`) |
| Cópia usada | `Downloads/2026_HIST_8ANO_AVALIAÇÃO_ADAPTADA_2TRIMESTRE_CAIC.docx` — 24.355.548 bytes (5 bytes de diferença de metadados; mesmo nome e tamanho da linha do inventário) | `saida/fase-4/` |
| Tema | Revolução Industrial, Revolução Francesa, Napoleão, independências da América | Revolução Industrial: fábricas, cidades e trabalho |
| Habilidade | 10 questões com código no enunciado (`EF08HI03`, `EF08HI04`, `EF08HI07`), sem página e sem texto literal; uma questão traz só “Habilidade BNCC” | `EF08HI03X` (p. 570), cópia literal do catálogo, no log e nos metadados do arquivo |
| Entrada | — | [`atividade-revolucao-industrial-adaptado.json`](../../saida/fase-4/atividade-revolucao-industrial-adaptado.json) |
| Gabarito | na mesma peça, em página de uso do professor | arquivo separado (`…-gabarito.docx`) |

### 1.2 Medidas objetivas

| Métrica | Baseline (mão) | Gerada |
|---|---|---|
| Páginas | 7 | 1 |
| Questões | 10 | 10 |
| Palavras (corpo) | 577 | 300 |
| Frases | 43 | 17 |
| Média de palavras por frase | 13,4 | 17,6 |
| Parágrafos com texto | 67 | 14 |
| Tabelas | 1 (6 células) | 1 (8 células, 4 pares) |
| Imagens | 8 | 0 |
| Citações de fonte | 1 no documento (“Fonte: ilustração/reconstrução elaborada para fins didáticos”) | 8 (2 obras primárias, após cada leitura e cada item) |
| Código impresso na folha do estudante | não | não (vai nos metadados e no log) |

### 1.3 O que o par mostra

**Paridade de quantidade, diferença de forma.** As duas peças têm 10 questões; a
diferença está no *tipo* de resposta: o baseline resolve quase tudo com imagem e
marcação, a gerada com escrita curta e ligação de colunas.

**Onde a v1 ganha é rastreabilidade, não pedagogia** — código com página, fonte
por fato, gabarito separado e log são coisas que o baseline não tem.

**Onde a v1 perde é no que o estudante toca** — imagem para apontar e registro de
mediação.

---

## 2. Par 2 — Descolonização da África e da Ásia (9º ano)

### 2.1 Os dois documentos

| | Adaptada à mão (baseline) | Gerada pelo pipeline |
|---|---|---|
| Arquivo | `Atividade_Adaptada_Descolonizacao_Suporte3.docx` | `descolonizacao-da-africa-e-da-asia.docx` |
| Origem | cópia do `Downloads/` do professor — 12.829 bytes, MD5 `d673fa5864ad5ef7ca9963d2cb7fc584`; **não há linha no `drive-audit/inventory.csv`** (arquivo local, não sincronizado do Drive) | `montar` + `finalizar` (log em `saida/fase-4/registros.jsonl`) |
| Cópia usada | `saida/fase-4/descolonizacao-suporte3-adaptada.docx` (cópia idêntica da anterior) | `saida/fase-4/` |
| Tema | Descolonização da África (Angola, Mandela, palavras-chave) | Descolonização da África e da Ásia (Gana, Índia, Argélia, Angola, apartheid) |
| Série e suporte | 9º ano, **suporte 3** (“suposição a partir do pedido”, diz o documento) | 9º ano, **suporte 2** (único nível implementado na v1) |
| Habilidade | “Código não verificado — não atribuir como definitivo. Conferir na BNCC e no CRMG antes do registro.” | `EF09HI31X` (p. 577), texto literal do catálogo, tipo `alterada` |
| Entrada | — | [`atividade-descolonizacao-africa-asia-adaptado.json`](../../saida/fase-4/atividade-descolonizacao-africa-asia-adaptado.json) |
| Estrutura | 5 tarefas em 5 páginas + caderno do professor (objetivo, duração, metodologia, recursos, avaliação, público/PDI, 7 orientações de aplicação) + registro de desempenho; gabarito na mesma peça | 2 blocos de leitura com pergunta, 4 itens de completar, 4 pares de ligar; gabarito em arquivo separado |

### 2.2 Medidas objetivas

| Métrica | Baseline (mão) | Gerada |
|---|---|---|
| Páginas | 11 | 1 |
| Palavras (corpo + tabelas) | 674 | 352 |
| Frases (fora das tabelas) | 38 | 29 |
| Média de palavras por frase | 17,7 | 12,1 |
| Parágrafos com texto | 53 | 14 |
| Tabelas / células | 9 / 192 | 1 / 8 |
| Imagens | 0 | 0 |
| Fonte e corpo | Arial, 11 a 22 pt (títulos 20–22) | Arial 12 pt |
| Margens | 1,6 cm | 2,0 cm |
| Cabeçalho / rodapé | vazio / vazio | vazio / `template 1.0` |
| Campos de identificação | “Nome: ___ Data: ___” em **cada** uma das 5 tarefas | ausente (proibido por design) |
| Citações de fonte | 0 | 8 |
| Código da habilidade | declarado **não verificado** no próprio texto | `EF09HI31X` + p. 577 nos metadados e no log |
| Gabarito | na mesma peça (seção final) | arquivo separado (54 palavras) |

Custo medido nesta máquina: `verificar` **0,27 s**, `montar` **0,19 s**,
`finalizar` **0,16 s** (determinístico, sem rede, sem chamada de modelo).

### 2.3 O que o par mostra

1. **O baseline confessa a falta do catálogo.** A linha “Código não verificado —
   não atribuir como definitivo” é a evidência mais forte já registrada a favor
   do gate de habilidade da v1 (G1): o professor sabe que precisa ancorar o
   código e, sem catálogo, escreve o aviso no papel.
2. **A tarefa é mais simples do que o item da v1.** As 5 tarefas do baseline são:
   ler frases curtas e pintar uma palavra; ligar palavras **iguais**; caçar
   palavras num quadro de letras; completar a **letra** que falta; pintar SIM ou
   NÃO. Nenhuma exige produzir uma palavra inteira de memória. A folha gerada
   pede completar palavra inteira a partir de um banco de 12 e ligar coluna a
   coluna — exigência maior, para um público que o baseline atende com letra e
   pintura.
3. **Densidade não é propriedade do template.** No par 1 a gerada tinha frases
   mais longas (17,6 contra 13,4); aqui tem mais curtas (12,1 contra 17,7). O
   que muda é o texto que a sessão de redação escreveu — a regra “frases curtas”
   precisa estar no prompt e ser medida por peça, não presumida.
4. **Página não mede esforço.** As 11 páginas do baseline vêm de uma tarefa por
   página com “Nome/Data” repetido cinco vezes — é decisão pedagógica (“entregue
   uma página por vez”), não volume de conteúdo.
5. **Nenhum dos dois imprime o código na folha do estudante.** A gerada registra
   `EF09HI31X` nos metadados e no log; o baseline não registra em lugar nenhum.
   Isso confirma que o código é rastreabilidade de bastidor, não texto da folha.

### 2.4 Defeito que o par expôs — corrigido

O baseline é suporte 3 e a v1 só tem receita de suporte 2. Ao montar a
contraparte, `nivel_suporte: 3` no `atividade.json` era **aceito em silêncio**:
a folha saía com todo o desenho de suporte 2 e o log registrava `nivel_suporte:
3`. Um documento que se apresenta como suporte 3 sem ser é pior do que a recusa.

Corrigido em [`entrada.py`](../../src/historia_gen/entrada.py): qualquer nível
diferente de 2 passou a gerar reprovação com o motivo (“só o suporte 2 tem
receita validada”) e a folha não é gerada. **Atualizado no template 1.7:** o
suporte 3 agora tem receita própria — uma tarefa por página (GAP-7) —, então a
regra ficou: nível 1 recusado, nível 3 só no modo adaptado. Coberto por
`test_suporte_3_so_existe_no_modo_adaptado` e
`test_nivel_de_suporte_fora_da_receita_recusa_montagem`.

---

## 3. Par 3 — Roma Antiga (6º ano, atividade regular)

O primeiro par com **folha de atividade regular dos dois lados** — sem suporte
adaptado de um lado nem prova adaptada do outro.

### 3.1 Os dois documentos

| | Feita à mão (baseline) | Gerada pelo pipeline |
|---|---|---|
| Arquivo | `roma-antiga-regular-baseline.docx` (cópia de `3pprhistoria6ano.docx`, 41.314 bytes, MD5 `09fee60cfedb9dcf189a69b2b046c375`) | `roma-antiga-monarquia-republica-e-imperio.docx` |
| Origem | arquivo do professor no `Downloads/`; **nenhuma linha do `drive-audit/inventory.csv` corresponde por hash** — procedência declarada como cópia local, não sincronizada | `montar` + `finalizar` (log em `saida/fase-4/registros.jsonl`) |
| Tema | Roma Antiga: fundação, povos itálicos, República, plebeus, expansionismo, Império | Roma Antiga: monarquia, República e Império |
| Série e modo | 6º ano, **regular** | 6º ano, **regular** (`modo: "regular"`) |
| Habilidade | nenhum código no texto (nem BNCC, nem CRMG) | `EF06HI11X` (p. 566), texto literal do catálogo, nos metadados e no log |
| Estrutura | 13 questões: 6 dissertativas e 7 de múltipla escolha com 5 alternativas em letras, **sem espaço de marcação** | 1 leitura com fonte, 2 itens de marcar, 2 de V/F, 3 de completar, 3 pares de ligar |
| Gabarito | **não há** | arquivo separado (84 palavras) |
| Entrada | — | [`atividade-roma-antiga-regular.json`](../../saida/fase-4/atividade-roma-antiga-regular.json) |

### 3.2 Medidas objetivas

| Métrica | Baseline (mão) | Gerada |
|---|---|---|
| Páginas | 3 | 2 |
| Questões | 13 | 10 |
| Palavras (corpo + tabelas) | 561 | 437 |
| Frases | 35 | 55 |
| Média de palavras por frase | 16,0 | 7,9 |
| Parágrafos com texto | 63 | 23 |
| Tabelas / células | 0 / 0 | 1 / 6 |
| Imagens | 0 | 0 |
| Fonte e corpos | Arial, **3,5 a 10 pt** (seis tamanhos) | Arial 11 pt (um tamanho) |
| Margens | 1,0 / 1,0 / 1,2 / **3,1** cm | 2,0 cm nas quatro |
| Cabeçalho / rodapé | vazio / vazio | vazio / `template 1.2` |
| Citações de fonte | 0 | 9 |
| Espaços de marcação `( )` | 0 | 10 |
| Código da habilidade | nenhum | metadados e log (`EF06HI11X`, p. 566) |
| Gabarito | ausente | arquivo separado |

Custo medido: `verificar` **0,13 s**, `montar` **0,18 s**.

### 3.3 O que o par mostra

1. **O material regular de mão também não tem rastreabilidade.** Nenhum código,
   nenhuma fonte citada, nenhum gabarito — em 13 questões que misturam dissertativa
   e múltipla escolha. É o terceiro baseline seguido sem código de habilidade.
2. **Densidade é a menor dos quatro pares** (7,9 palavras por frase contra 16,0):
   efeito dos itens de marcar/V/F, que são frases curtas — não significa leitura
   mais fácil, porque o texto-base continua longo.
3. **Tipografia:** o baseline usa seis corpos (3,5 a 10 pt) e margem inferior de
   3,1 cm; a gerada usa um corpo (11 pt) e margens iguais. Ganha legibilidade,
   perde a hierarquia de títulos que o professor usa para separar questão de
   alternativa.
4. **Múltipla escolha sem marcação:** as 7 objetivas listam alternativas soltas em
   letras, sem `( )` — o estudante transcreve a letra. A gerada imprime `( )` em
   cada opção (v1.1), o que resolve a marcação mas não o apontar/circular.
5. **A segunda página é custo da citação.** 10 questões com 9 citações de fonte
   ocupam 2 páginas, contra 3 páginas do baseline com 13 questões — mesma
   observação do par 2: repetir a fonte por item é o que enche a folha.
6. **O GAP-5 (identificação) não aparece aqui.** O baseline regular não tem nome,
   turma nem escola; a numeração das questões basta. Isso enfraquece o argumento
   de que a folha sem identificação é um problema geral.

## 4. Par 4 — Reforma Protestante e Contrarreforma (7º ano)

O primeiro par com **avaliação adaptada de mão de 7º ano** e uma folha gerada
que já usa ficha de planejamento e caixa de vocabulário (templates 1.8 e 1.9).

### 4.1 Os dois documentos

| | Adaptada à mão (baseline) | Gerada pelo pipeline |
|---|---|---|
| Arquivo | `2026_HIST_7ANO_AVALIAÇÃO_ADAPTADAS_2TRIMESTRE_CORACI.docx` | `reforma-protestante-e-contrarreforma.docx` |
| Origem | Google Doc do Drive — id `1b_H2veIUJWyZih9zCFfA2vgus50FTB_GBBsmpItDWlQ`, modificado em 2026-08-14; exportado em `.docx` em 2026-11-04 (7.115.028 bytes, MD5 `768b2386b9203d287bc51c26d59ec998`). Export de Google Doc pode variar de tamanho entre execuções | `montar` (log em `saida/fase-4/par-4/registros.jsonl`); **sem `finalizar`** — a revisão humana do par ainda não foi registrada |
| Tema | Grandes Navegações, Reforma Protestante e Contrarreforma | Reforma Protestante e Contrarreforma |
| Série e modo | 7º ano, **adaptada** (o título diz “AVALIAÇÃO TRIMESTRAL ADAPTADA”) | 7º ano, **adaptado**, suporte 2 |
| Habilidade | **três códigos misturados** (`EF07HI02`, `EF07HI05`, `EF07HI06`), sem página e sem texto literal; uma questão não traz código | `EF07HI05X` (p. 568), texto literal do catálogo, nos metadados e no log |
| Estrutura | 10 números (01–10), mas o **06 aparece duas vezes** — 11 itens; múltipla escolha com 2–3 opções, completar com quadro de palavras e ligar termo–desenho | 2 blocos de leitura com pergunta, 2 itens de marcar, 2 de V/F, 2 de completar e 1 ligar de 2 pares |
| Identificação | tabela de cabeçalho com Nome, Data, Disciplina, Valor e “Nota conquistada” | ausente (proibido por design) |
| Registro / planejamento | **não há** | página do professor com ficha de planejamento, grade de mediação e orientações |
| Gabarito | **não há** | arquivo separado |
| Entrada | — | [`atividade-reforma-protestante-adaptado.json`](../../saida/fase-4/atividade-reforma-protestante-adaptado.json) |

### 4.2 Medidas objetivas

| Métrica | Baseline (mão) | Gerada |
|---|---|---|
| Páginas | 5 | 3 (2 do estudante + 1 do professor) |
| Questões | 10 números / 11 itens | 10 |
| Palavras (corpo + tabelas) | 526 | 552 |
| Frases (fora das tabelas) | 53 | 33 |
| Média de palavras por frase | **9,9** | **16,7** |
| Parágrafos com texto | 42 | 39 |
| Tabelas / células | 5 / 10 | 5 / 50 (inclui a grade do professor) |
| Imagens | **8** (2+2+1+1+2 por página) | 0 |
| Citações de fonte | 2 menções (URL de um mapa e aviso de imagem), sem autor/ano/acesso | toda leitura e todo item com citação (2 obras, uma primária) |
| Código impresso na folha do estudante | 3 códigos diferentes por questão | não (metadados e log) |
| Caixa de vocabulário | não | 4 palavras-chave no topo |
| Gabarito | ausente | arquivo separado |

### 4.3 O que o par mostra

1. **A avaliação adaptada mistura habilidades.** Três códigos em 10 números e
   uma questão sem código: o mesmo problema do par 1, agora numa peça adaptada.
   A folha gerada ancora **uma** habilidade com página e texto literal — é o
   ganho G1 se repetindo no quarto baseline.
2. **A identificação aparece também na adaptada.** Nome, data, disciplina,
   valor e nota estão no cabeçalho — o quarto baseline seguido com campos que a
   v1 proíbe. Isso reforça a decisão de tratá-los como opção (GAP-5), não como
   padrão automático.
3. **O registro do professor continua ausente no material de mão.** Nem grade de
   mediação, nem objetivo/duração/metodologia, nem orientações de aplicação — a
   peça é só a prova. Do lado gerado, a página do professor traz ficha, grade e
   orientações, agora também no 7º ano (GAP-2).
4. **A imagem é o apoio que a v1 ainda não tem.** Oito imagens em cinco páginas,
   uma por questão em boa parte delas, contra zero na folha gerada. É o GAP-1/GAP-4
   no seu formato mais concreto — para uma adaptação de 7º ano, a figura não é
   enfeite, é o enunciado.
5. **A gerada escreve mais longo.** 16,7 palavras por frase contra 9,9 do
   baseline, o inverso do par 1 e o mesmo sinal do par 2: a regra “frases curtas”
   é da redação, não do template, e nesta folha ainda não foi cumprida. Fica
   registrado como pendência de redação, não como defeito de layout.
6. **A numeração do baseline tem defeito.** O “QUESTÃO 06” aparece duas vezes e
   a folha vai a 5 páginas; a gerada numera 10 itens sem repetição e fecha em 3
   páginas — duas delas de conteúdo do estudante.
7. **Custo de página não é custo de aprendizagem.** A gerada tem menos páginas e
   mais palavras; o baseline tem mais páginas e imagens. A comparação de
   densidade (9,9 contra 16,7) mostra que a folha gerada não é “mais fácil” por
   ser mais curta.

---

## 5. O que os quatro baselines têm e a gerada não (lacunas da v1)

| # | Lacuna | Evidência no par 1 | Evidência no par 2 | Impacto |
|---|---|---|---|---|
| GAP-1 | **Resposta de baixa exigência motora**: pintar, circular, apontar, marcar em vez de escrever | 8 imagens; “marque com um (X) a imagem”, “circule a imagem”, “pinte a palavra” | pintar LIBERDADE, ligar palavras iguais, caça-palavras, completar a letra, pintar SIM/NÃO | **alto** — é a forma de resposta que define a adaptação real; **implementado na v1.1 (templates 1.2 a 1.4)** para marcar, V/F, parear iguais, ordenação e figura de apoio; o caça-palavras fica fora por decisão do design aprovado (Alternativa F). No par 3 (regular) a marcação também falta: 7 objetivas com alternativas soltas, sem `( )` |
| GAP-2 | **Registro da mediação** e caderno do professor | “REGISTRO DA MEDIAÇÃO”, “OBSERVAÇÃO DO PROFESSOR” | tabela “Registro de desempenho” (5 tarefas × sozinho / apoio parcial / apoio total) + objetivo, duração, metodologia, recursos, avaliação, público/PDI, 7 orientações de aplicação | **alto** — é o que transforma a folha em instrumento de acompanhamento; **confirmado nos dois pares adaptados** e **implementado na v1.1** (página final opcional, ver “O que isso muda no plano”); o par 3 (regular) não traz registro |
| GAP-3 | **Orientações de aplicação** para quem mediaia | tabela “Perfil → Ajuste” na versão de referência local | 7 passos (uma página por vez, ler em voz alta, aceitar CAA, respeitar pausas…) | médio — hoje o professor decide sozinho como aplicar |
| GAP-4 | **Variedade de item**: verdadeiro/falso, ordenação, múltipla escolha, caça-palavras | 6 alternativas `( )`, itens de marcar | SIM/NÃO, caça-palavras, completar letra | médio — **V/F, marcar com opções, ordenação e parear iguais implementados (templates 1.2 e 1.3)**; caça-palavras segue fora por decisão do design aprovado (Alternativa F) |
| GAP-5 | **Identificação** (escola, nome, turma/data) | cabeçalho com escola, endereço e “Nome/Turma” | “Nome / Data” repetido em cada tarefa | decisão consciente do design (folha sem cabeçalho); reavaliar com o professor, que usa esses campos nos dois formatos |
| GAP-6 | **Glossário / palavras-chave destacadas** antes das tarefas | glossário na versão de referência local | 4 palavras-chave fixas (ÁFRICA, ANGOLA, MANDELA, PAZ) que percorrem as tarefas | baixo/médio — **implementado no template 1.9**: `vocabulario` opcional abre a folha com a caixa de palavras-chave e volta em cada tarefa do suporte 3; sem o campo, nada muda |
| GAP-7 | **Uma tarefa por página** (para entregar e recolher por vez) | — | 5 tarefas em 5 páginas + 1 página de caderno do professor | **implementado na v1.1 (template 1.7)** no modo adaptado com `nivel_suporte: 3`: cada bloco de leitura e cada item abrem página nova e a página repete instrução, banco de palavras e fontes (a anterior já foi recolhida). Folha de 7 tarefas = 7 páginas + a do professor; o suporte 2 segue em folha corrida |

**O que o par 3 acrescenta às lacunas:** GAP-2/GAP-3, nada — atividade regular
não traz registro nem orientações de aplicação. GAP-4, o baseline tem **múltipla
escolha com 5 alternativas (a–e)** e questões dissertativas; a v1.1 cobre V/F e
marcar com 2–4 opções, não cobre alternativa longa nem dissertativa. GAP-5, o
baseline **não** usa campos de identificação. GAP-6, sem glossário e sem banco de
palavras.

**O que o par 4 acrescenta às lacunas:** GAP-1/GAP-4, **8 imagens** como apoio de
leitura — o baseline resolve metade dos itens com figura, e a v1 não tem figura
nesta folha (o suporte a `figuras` existe, mas nenhuma foi usada). GAP-2/GAP-3,
nada — prova adaptada sem registro nem orientações, como o par 2. GAP-5, o
baseline **usa** Nome/Data/Disciplina/Valor/Nota. GAP-6, sem glossário, mas com
**três habilidades** misturadas no enunciado — a lacuna de rastreabilidade (G1)
continua no material adaptado.

## 6. O que a gerada tem e os quatro baselines não (ganhos da v1)

| # | Ganho | Evidência |
|---|---|---|
| G1 | Código de habilidade **ancorado no catálogo** (código + página + texto literal + tipo de modificação) | `EF08HI03X` p. 570, `EF09HI31X` p. 577 e `EF06HI11X` p. 566 nos metadados e no log; o baseline 2 escreve “código não verificado”, o 3 não tem código algum e o 1 mistura “BNCC” e “BNCC/CRMG” sem página |
| G2 | **Fonte por fato**, com autor, ano e data de acesso | 8 a 9 citações em cada folha gerada; 1 no baseline 1, **nenhuma** nos baselines 2 e 3 |
| G3 | **Gabarito em arquivo separado** | os dois baselines trazem o gabarito na peça do estudante |
| G4 | **Auditoria e reproducibilidade** | hash da entrada, versão do catálogo, semente do embaralhamento; mesma semente ⇒ mesmo layout |
| G5 | **Recusa determinística** de entrada inválida | código fora do catálogo, ano divergente, falta de confirmação do professor e, agora, nível de suporte não implementado |

## 7. Leitura conjunta

1. **A lacuna central não é “imagem”, é modo de resposta.** No par 1 a forma é a
   figura; no par 2, sem uma única imagem, o baseline ainda responde pintando,
   pareando, caçando letras e marcando SIM/NÃO. O que falta na v1 é a **escada de
   exigência** (marcar → parear → escrever), não o arquivo de figura.
2. **GAP-2 é a lacuna mais bem corroborada.** Dois baselines independentes, de
   séries e escolas diferentes, trazem registro de mediação e orientação de
   aplicação. É o item de v1.1 com mais evidência e o mais barato de gerar (não
   depende de IA: são campos e uma tabela).
3. **Densidade do texto varia com a redação, não com o template.** O par 2
   inverte o resultado do par 1 — a regra “frases curtas” precisa ser instrução de
   redação, verificada por medição em cada peça.
4. **O ganho de rastreabilidade se repete e é o único consenso entre os pares.**
   Nenhum dos dois baselines consegue dizer, olhando o papel, de que habilidade
   do CRMG a folha veio — um deles escreve isso explicitamente.
5. **O professor paga a rastreabilidade em páginas e campos.** 7, 11, 3 e 5
   páginas conforme a peça; gabarito junto nos pares 1 e 2, ausente nos pares 3 e
   4. A v1 devolve folhas mais curtas e gabarito separado, mas tira do professor
   o registro que ele usa em sala — quando ele usa (par 2); nos pares 1 e 4 nem
   o material de mão trazia registro.
6. **O único consenso dos quatro pares é a falta de rastreabilidade no material
   de mão:** nenhum dos quatro baselines diz de que página do CRMG a peça veio, e
   um deles escreve que o código não foi verificado; o par 4 chega a misturar
   três códigos sem página. O ganho de G1 deixa de ser inferência de um caso e
   passa a valer para quatro.

## 8. O que isso muda no plano

Sugestões de v1.1, em ordem de evidência (não decididas aqui):

1. **Registro de mediação + orientações de aplicação** (GAP-2, GAP-3) —
   **implementado no template 1.1**: `registro_mediacao: true` acrescenta uma
   página final de uso do professor (como aplicar + grade por item com sozinho /
   apoio parcial / apoio total + data, tempo e observações), marcada como página
   que não vai para o estudante; `orientacoes_aplicacao` recebe as orientações
   próprias do professor. O **cabeçalho de caderno** (objetivo, duração,
   metodologia, recursos, público/PDI) entrou no template 1.8 como
   `planejamento` opcional, impresso no topo da página do professor.
2. **Modos de resposta de baixa exigência** (GAP-1, GAP-4) — **implementado no
   template 1.2** (`itens_marcar` com 2–4 opções e espaço `( )`; `itens_vf` com
   correção obrigatória na afirmação falsa) **e no 1.3** (`itens_parear`: mesma
   palavra nas duas colunas; `itens_ordenar`: sequência embaralhada para numerar,
   com o gabarito na ordem certa; `figuras`: PNG/JPEG local de até 14 cm de
   largura e 17 cm de altura, centralizada, legenda e citação, com recusa de
   imagem ausente ou em formato não aceito — medidas conferidas em impressão real
   no template 1.4). O **caça-palavras** segue fora por decisão do design aprovado
   (Alternativa F: layout difícil de automatizar bem em `.docx`, e há geradores
   gratuitos) — reabrir só com pedido do professor.
3. **Uma tarefa por página no suporte 3** (GAP-7) — **implementada no template
   1.7**: `nivel_suporte: 3` no modo adaptado monta uma tarefa por página. O
   **perfil** de suporte 3, porém, continua incompleto: a receita de redação
   (PDI, comunicação alternativa, uma habilidade por folha) não existe, e a Q1
   (quem produz esse material — professor ou AEE) segue em aberto.
4. **Identificação** (GAP-5): decidir com o professor — os baselines adaptados usam
   nome/turma/data, o regular não usa nada, e a v1 proíbe os campos por design. O
   par 3 tira a urgência do item: pode virar opção, não padrão.
5. **Palavras-chave/glossário** (GAP-6): **implementado no template 1.9** como
   `vocabulario` opcional (até 8 palavras), e não como reaproveitamento do banco
   de palavras — o banco mistura respostas e distratores, então imprimi-lo no
   topo ensinaria a palavra errada. A caixa abre a folha e se repete em cada
   tarefa do suporte 3.

## Limitações deste comparativo

- **Quatro pares**, dentro da faixa 3–5 que a Fase 4 pede; as conclusões são de
  desenho, não estatística. Os pares 1, 2 e 4 comparam peças **adaptadas**
  (avaliação, caderno de suporte 3 e avaliação de 7º ano); o par 3 é o único com
  folha **regular** dos dois lados.
- **O baseline do par 4 é um Google Doc exportado** em `.docx` em 2026-11-04; o
  tamanho e o MD5 registrados valem para essa exportação, que pode variar entre
  execuções. O PDF usado nas contagens foi gerado no LibreOffice a partir dela.
- **Suporte diferente no par 2**: o baseline é suporte 3 e a folha gerada é
  suporte 2 — é a comparação possível hoje, e a diferença está declarada em vez
  de escondida (o nível 3 agora é recusado na entrada).
- **Sem medição de tempo de adaptação manual** (Q5 segue pendente): nenhuma
  afirmação de ganho de tempo é feita aqui.
- Contagem de páginas obtida convertendo para PDF no LibreOffice; a quebra exata
  no Word pode diferir (as margens e os corpos são os registrados).
- A cópia do baseline 1 tem 5 bytes de diferença do arquivo do inventário; as dos
  baselines 2 e 3 **não estão no inventário** (arquivos locais do professor, sem
  hash correspondente) — as três procedências estão declaradas acima com tamanho e
  MD5.
- As folhas destes pares usaram a **cópia de teste aprovada** do catálogo; desde
  2026-11-03 o catálogo versionado também está aprovado (conferência literal das
  97 linhas contra o PDF), então `montar` não depende mais de cópia paralela.
- O pipeline não verifica o conteúdo das fontes citadas: `EF09HI31X` está ancorado
  no catálogo, mas os fatos do texto (1957, 1947, 1962, 1975, 1994) vêm da redação
  e da obra citada, não de uma checagem automática.
