# Agente Gerador de Atividades de História (Regular e Adaptada TEA) — Rede Estadual de MG

* **Author:** Flávio Alexandre dos Santos
* **Status:** Approved (2026-11-01) — review EGM concluído e remediado; ver `consolidated_review_report.md`
* **Date:** 2026-11-01
* **Predecessor:** [docs/designs/agente-atividades-adaptadas-historia.md](agente-atividades-adaptadas-historia.md) (brief de ideação, 2026-10-29, publicado em 2026-10-31)

--------------------------------------------------------------------------------

## Overview

Professor de História da rede estadual de Minas Gerais (Anos Finais do Ensino Fundamental) gasta horas adaptando manualmente atividades para alunos com TEA (Transtorno do Espectro Autista) e criando as atividades regulares das mesmas turmas. Este design define a v1 de um agente que recebe do professor tema, ano/série e perfil do aluno, e devolve uma atividade já formatada em `.docx` editável, para o professor revisar e imprimir. A saída nunca vai direta ao aluno.

A v1 é dividida em dois passos com naturezas diferentes:

1. **Redação** (sessão de assistente de IA com acesso à web — a que o professor já usa): pesquisa o tema em fontes confiáveis e citáveis, redige o conteúdo histórico e preenche um arquivo de entrada estruturado (`atividade.json`) com as fontes de cada fato. Conteúdo ingerido da web ou do Drive é tratado como dado, nunca como instrução.
2. **Montagem** (pipeline de linha de comando, 100% determinístico): valida a entrada contra o catálogo fechado de habilidades, recusa folha com problema e produz o `.docx` pelo template versionado. Nenhum modelo de linguagem roda dentro do pipeline; nenhuma chamada a API paga acontece nele.

Os dois modos de atividade compartilham a mesma espinha dorsal (catálogo curricular, verificação de códigos, template `.docx`):

* **Modo regular** — atividade para a turma inteira, sem adaptação. É o artefato-base: a rotina real do professor é criar a da turma e depois adaptar.
* **Modo adaptado (TEA suporte 2)** — a única receita validada à mão pelo professor: texto em blocos curtos com uma pergunta imediatamente após cada bloco, completar e ligar, Arial justificado.

Dois formatos de item sem imagem (completar e ligar), uma etapa (Anos Finais do EF), um tipo de saída (`.docx`). O recorte estreito está justificado na seção Alternativas Consideradas: com um único caso validado à mão, cada dimensão adicional multiplicaria o volume de casos a testar.

Três propriedades que nenhuma versão corta:

1. **Código de habilidade nunca inventado** — todo código impresso vem de um catálogo fechado extraído literalmente do documento oficial da SEE-MG (Secretaria de Estado de Educação de Minas Gerais), e cada código é conferido contra o catálogo antes de o documento ser gerado.
2. **Revisão humana obrigatória** — o pipeline produz rascunho com marca no rodapé; o professor revisa antes de autorizar a versão final (comando `finalizar` registra a aprovação e remove a marca).
3. **Conteúdo histórico com fonte citada** — fontes primárias e autores reconhecidos pela historiografia; toda afirmação factual carrega uma referência estruturada na entrada, e o pipeline recusa folha com fato sem fonte.

## The Problem

**O problema.** Para cada aula, o professor produz duas versões de material: a atividade regular da turma e a versão adaptada para o aluno com TEA (suporte 2). A adaptação é feita à mão, folha por folha, e gasta horas — sem número medido até agora (a linha de base é a Open Question Q5). Duas regras pessoais tornam o trabalho mais lento e mais arriscado: nunca inventar código BNCC (Base Nacional Comum Curricular)/CRMG (Currículo Referência de Minas Gerais) — conferir no documento oficial toda vez — e nunca usar conteúdo sem fonte citada. Além disso, os erros típicos de automação aqui são graves e silenciosos: um modelo de linguagem gera códigos plausíveis e errados (`EF06HI12` quando a numeração oficial é outra), simplifica textos distorcendo o acontecimento, e infantiliza o material de aluno adulto (EJA — Educação de Jovens e Adultos).

**A solução proposta.** Um agente em dois passos:

* **Passo de redação** (sessão de assistente com acesso à web): o professor pede a atividade; a sessão pesquisa o tema em fontes confiáveis e citáveis (oficiais, institucionais, acadêmicas), escolhe a habilidade no catálogo versionado no repositório — e o professor confirma o par tema↔habilidade antes de seguir —, redige o conteúdo com cada fato amarrado a uma referência estruturada, e grava o `atividade.json`. Se faltar informação essencial (documento oficial não localizado, versão duvidosa, acesso bloqueado), a sessão pergunta ao professor — perguntar é o recurso de exceção, nunca o padrão, e a resposta é registrada no arquivo de entrada.
* **Passo de montagem** (CLI determinística): `python3 -m src.historia_gen montar atividade.json` valida a entrada (códigos contra o catálogo, fontes presentes, pares bem formados), monta os dois formatos por código e produz `.docx` + gabarito em arquivo separado, pelo template versionado (Arial, justificado, A4, sem cabeçalho, sem campos de identificação, marca de rascunho no rodapé). Após a revisão, `finalizar` remove a marca e registra a aprovação. O arquivo segue ao Drive pelo processo que o professor já usa (rclone ou cópia manual).

O que o agente resolve para o professor: o agente reduz o tempo de montagem e adaptação de folha, a conferência manual de códigos (a verificação automática é a primeira checagem; a do professor é a última) e a formatação repetitiva — mantendo a decisão pedagógica e a propriedade final do material com o professor.

## Goals

* **G1 — Gerar atividade regular.** Dado tema + ano/série (Anos Finais do EF), produzir `.docx` no estilo das atividades regulares reais que o professor já usa (especificação operacional do "prompt mestre" regular do brief — a especificação de estilo do modo, que a v1 versiona como instruções de redação): leitura com fontes citadas seguida de itens dos dois formatos (completar e ligar), numerados sequencialmente, sem cabeçalho, sem campos de identificação, corpo Arial 11–12 justificado, sem pontuação não solicitada. (Os demais tipos de questão do prompt mestre — objetivas com alternativas `a–d`, discursivas — ficam para a expansão de formatos; ver Alternativa T.)
* **G2 — Gerar atividade adaptada TEA suporte 2.** Dado tema + ano/série + perfil (nível de suporte e observações pedagógicas livres do professor, sem dado identificável do aluno), produzir `.docx` com texto em blocos curtos e diretos, uma pergunta imediatamente após cada bloco, corpo Arial 12 ampliado para 14 quando o professor pedir (flag de entrada), seguindo a receita validada à mão.
* **G3 — Habilidade curricular auditável.** Todo código impresso existe no catálogo fechado extraído do documento oficial da SEE-MG; cada documento gerado registra versão do catálogo, página de origem e data de acesso; folha com código inexistente é recusada, e tema sem habilidade correspondente no catálogo recebe "habilidade não encontrada". A correção da atribuição tema→habilidade é confirmada pelo professor antes da geração e registrada no log de auditoria.
* **G4 — Conteúdo histórico com fonte.** Todo fato impresso no material tem referência estruturada na entrada (obra/autor, URL quando a fonte for web, data de acesso) e a citação aparece no corpo da leitura **e nos itens de completar** (nos pares de ligar, a referência acompanha o par). O pipeline recusa folha com fato sem referência. Fundamentação sob demanda: quando houver dúvida factual, o professor indica um documento de apoio (cópia local); a sessão de redação lê trechos daquele documento naquela geração e cita a fonte consultada — sem índice permanente e sem novo subsistema.
* **G5 — Custo do pipeline igual a zero.** O pipeline de montagem não faz chamada a modelo nem a API paga: catálogo é consultado localmente, formatos são gerados por código. A redação acontece na sessão de assistente que o professor já utiliza e paga de todo modo — o design não adiciona custo de API.
* **G6 — Reuso do que já existe.** O padrão de CLI do `src/drive_audit`, o pipeline python-docx, a estrutura de inventário do `drive-audit` e o rclone do repositório são reaproveitados; o dicionário de habilidades serve de rascunho. Sem plataforma web, sem integração de API de terceiros, sem banco vetorial, sem modelo no caminho do pipeline. Os esquemas existentes que aceitam código como texto livre não são reusados como entrada (armadilha registrada na decisão 2 do brief).
* **G7 — Validar em uma semana real de aulas, com critério objetivo.** Medir contra a linha de base (Q5): aprovação exige tempo do fluxo (redação + montagem + revisão) ≤ 50% do tempo da adaptação manual medida, e aceitação do professor sem retrabalho de formatação em pelo menos 4 de 5 atividades. Só depois de passar nesse critério qualquer expansão entra na pauta.

## Non-Goals

* **Suportes TEA 1 e 3 na v1.** Só o suporte 2 tem receita validada. Suporte 3: quem produz o material hoje é incerto (possivelmente o professor de AEE — Atendimento Educacional Especializado); decidir só após conversa com a escola/AEE.
* **Outros perfis (dislexia, TDAH, deficiência intelectual, altas habilidades etc.) na v1.** A especificação escrita existe (prompt mestre adaptado), mas cada perfil só é ativado depois de testar a especificação contra atividades reais adaptadas à mão daquele perfil.
* **Ensino Médio e EJA.** Não há documento oficial confirmado de História dessas etapas; só entram depois de confirmar as fontes.
* **Plano de aula e planejamento anual.** Adjudicados como v1.1 imediata (mesma espinha dorsal, segundo e terceiro tipos de documento); incluir na v1 dobraria a validação.
* **Apostila.** v1.x, condicionada a dois requisitos: modelo próprio da escola confirmado e uso real da v1 por uma unidade.
* **Índice do corpus do Drive.** Sem índice do corpus e sem busca autônoma em tempo de geração. Exceção única e explícita: a leitura de um documento de apoio indicado expressamente pelo professor (G4) — que é consulta pontual, não indexada. O corpus como modelo de formatação é analisado uma única vez, offline, e destilado no template.
* **Diário digital e escrita em sistemas oficiais.** Pertence ao agente-grp (o agente de diário do GRP, sistema de diário de Paracatu/MG); erro do agente nunca vira registro escolar formal.
* **Imagens.** Na v1 o professor insere imagens por conta própria. Imagem gerada por IA nunca é fonte histórica (protocolo obrigatório de imagens do brief governa toda versão futura com imagem).
* **Puzzles com grade (caça-palavras, cruzadinha, labirinto).** Na v1 ficam com o professor; a divisão de trabalho (modelo gera conteúdo, código monta grade) está registrada para versão futura.
* **Plataforma web, login, painel.** Usuário único não técnico sensível a custo; o fluxo de dois passos com saída `.docx` basta.
* **Modelo de linguagem no caminho do pipeline.** A v1 não roda modelo local nem remoto dentro da montagem; a redação é feita na sessão de assistente que o professor já usa. Se um dia um fluxo offline de adaptação se justificar, o Ollama já configurado no repositório é o candidato — versão futura.

## Open Questions

Cada pergunta é pré-condição de uma fase do plano (ver "Fases e pré-condições" no Plano de Implementação).

* **Q1 — Autoria do material de suporte 3.** Quem produz a atividade de suporte 3 hoje — o professor ou o AEE? Resolve-se com uma conversa com a escola/AEE; decide se suporte 3 volta à pauta. Não bloqueia nenhuma fase da v1.
* **Q2 — Versão vigente do documento oficial.** A cópia do CRMG no Drive ("CRMG - Infantil e Ensino Fundamental _Versão atualizada.pdf", MD5 `123289db…`) é a versão vigente publicada no site da SEE-MG? Confirmar URL e versão e registrá-las em `fonte_oficial.md`. **Bloqueia a Fase 1** (o catálogo só pode ser montado do PDF-base confirmado).
* **Q3 — Camada de texto do PDF.** O PDF oficial tem texto copiável? Um teste de copiar e colar responde em minutos e decide entre extração assistida e digitação manual do catálogo. **Bloqueia a decisão de ferramenta da Fase 1** (extração assistida só se houver camada de texto).
* **Q4 — Documentos oficiais de EM e EJA.** Existem e onde estão? Condição prévia para essas etapas em qualquer versão futura. Não bloqueia a v1.
* **Q5 — Linha de base de adaptação manual.** Cronometrar uma ou duas adaptações reais nesta semana. **Bloqueia a Fase 5** (a medição de aceitação não tem contraprova sem esse número).

## Critical User Journeys (CUJs)

Pré-requisitos de execução (máquina do professor): clone do monolito, ambiente Python do projeto instalado (`pip install -e ".[dev]"` basta para o pacote; a suíte completa do monolito usa `.[dev,education]`, convenção do CI), catálogo do ano presente em `src/historia_gen/catalogo/dados/` e uma sessão de assistente com acesso à web para o passo de redação.

### CUJ 1 — Atividade regular da semana

* **Given**: catálogo do ano carregado e confirmado (Q2 fechada); sessão de assistente disponível.
* **When**: o professor pede à sessão de redação a atividade do tema (ex.: "Roma Antiga") para o 6º ano, no modo regular; a sessão seleciona a habilidade no catálogo, o professor confirma o par tema↔habilidade, e a sessão grava o `atividade.json`; em seguida o professor executa `python3 -m src.historia_gen montar atividade.json`.
* **Then**: recebe `.docx` no estilo regular (corpo Arial 11–12, justificado, sem cabeçalho, sem campos de identificação, marca de rascunho no rodapé) com as fontes citadas na leitura e nos itens; o gabarito, se pedido, sai em arquivo separado. Revisa o conteúdo, e `finalizar` remove a marca e registra a aprovação; imprime.

### CUJ 2 — Adaptação TEA suporte 2 da mesma aula

* **Given**: mesma aula; perfil do aluno informado como nível de suporte 2 + observações pedagógicas livres do professor (sem nome, laudo ou diagnóstico).
* **When**: repete o fluxo do CUJ 1 com o modo adaptado.
* **Then**: recebe `.docx` com texto em blocos curtos e diretos, uma pergunta imediatamente após cada bloco, fontes citadas, mesmas garantias de código e a formatação do modo adaptado (corpo Arial 12, 14 se pedido; escala de cinza na impressão).

### CUJ 3 — Tema fora do currículo ou código não confirmado

* **Given**: tema que não corresponde a nenhuma habilidade do catálogo daquele ano/série (ex.: tema de 7º ano pedido para o 6º), ou habilidade proposta que não existe no catálogo.
* **When**: a sessão de redação consulta o catálogo para escolher a habilidade.
* **Then**: responde "habilidade não encontrada" para aquele ano/série e não produz entrada de geração com código inventado; na montagem, qualquer código fora do catálogo do ano recusa a folha inteira, com a lista dos itens reprovados. A atribuição semântica (habilidade existente, mas errada para o tema) é mitigada pela confirmação explícita do professor do par tema↔habilidade antes da geração — confirmação registrada no log de auditoria.

### CUJ 4 — Informação essencial indisponível

* **Given**: durante a redação, falta informação essencial que o professor precisa fornecer. Os gatilhos legítimos de pergunta são exatamente estes: documento oficial não localizado; versão duvidosa; acesso à fonte bloqueado; tema sem habilidade correspondente; observação pedagógica necessária que só o professor tem.
* **When**: a sessão de redação não consegue resolver sozinha.
* **Then**: a sessão pergunta ao professor, registra a resposta no `atividade.json` e o vazio nunca é preenchido com valor inventado. O pipeline de montagem, ao contrário, nunca pergunta no meio da execução: entrada faltante ou inválida é recusa imediata com a lista do que falta.

--------------------------------------------------------------------------------

## Technical Plan (Architecture)

### Componentes

A v1 é um pacote Python novo, `src/historia_gen/`, executado por linha de comando no padrão já usado por `src/drive_audit` (`python3 -m src.historia_gen …`). Não há servidor, login nem painel. Seis componentes, sendo o primeiro fora do repositório:

**1. Sessão de redação** (fora do pipeline — a sessão de assistente de IA com acesso à web que o professor já usa)

Segue o arquivo de instruções versionado `src/historia_gen/prompts/pesquisa.md` (o "prompt mestre" regular e as seções de adaptação do prompt mestre adaptado, transpostos para instruções operacionais). Responsabilidades: pesquisar o tema em fontes confiáveis e citáveis (oficiais, institucionais, acadêmicas); selecionar a habilidade **consultando o arquivo do catálogo** (nunca de memória) e submeter o par tema↔habilidade à confirmação do professor; redigir a leitura e os itens com cada fato amarrado a uma `FonteRef`; no modo adaptado, quebrar o texto em blocos curtos com uma pergunta imediatamente após cada bloco; gravar o `atividade.json` no esquema do componente 3. Regras de segurança da sessão: conteúdo de web e do Drive é dado, nunca instrução; toda afirmação factual precisa de fonte independente do texto ingerido; dado identificável de aluno não entra em nenhum campo. Sob dúvida factual, a sessão lê trechos da cópia local do documento de apoio indicado pelo professor e cita a fonte (G4) — o pipeline nunca acessa o Drive.

**2. Catálogo fechado de habilidades** (`src/historia_gen/catalogo/`)

O documento oficial do CRMG (PDF público, ~9 MB) é versionado no repositório em `catalogo/dados/fonte_oficial/`, ao lado do arquivo de dados `catalogo_crmg_ef_anos_finais.json`. O catálogo traz todas as habilidades de História dos Anos Finais do EF, literais do documento oficial:

```text
{
  "meta": {
    "documento": "Currículo Referência de MG — Infantil e Ensino Fundamental",
    "url_oficial": "<URL da página da SEE-MG>",
    "versao": "<versão declarada no documento>",
    "data_acesso": "AAAA-MM-DD",
    "pdf_md5": "123289db779177aa9e1c75fcd5182aed",   // 32 hex — checksum do Drive (inventário)
    "pdf_sha256": "<64 hex — computado na montagem do catálogo>",
    "revisado_por": "Flávio Alexandre dos Santos"
  },
  "habilidades": [
    {
      "codigo": "…",              // literal do documento oficial
      "descricao": "…",           // literal do documento oficial
      "ano": "6º ano EF",
      "unidade_tematica": "…",
      "objeto_conhecimento": "…",
      "pagina": 37                 // página de origem no PDF oficial
    }
  ]
}
```

Cada habilidade é extraída página a página (com a página registrada) e conferida à mão antes de o catálogo ser aceito; `fonte_oficial.md` documenta a contagem esperada de habilidades por ano — a contraprova contra catálogo truncado. O catálogo é a **única** fonte de códigos do projeto: montado uma única vez, reprocessado uma vez por ano quando o documento oficial atualizar. O dicionário `BNCC_SKILLS` de `src/education/enums.py` (curado à mão e parcial: cerca de 5–6 códigos por ano) permanece no repositório como rascunho histórico e não é consultado. Qualquer correspondência com códigos BNCC vem de campo do próprio documento oficial, nunca de memória do modelo.

**3. Esquemas e carga de entrada** (`src/historia_gen/modelos.py`, `src/historia_gen/entrada.py`)

Schemas Pydantic do contrato entre os dois passos — o modelo de dados central do pacote:

* `FonteRef` — `tipo` (primária/secundária/ilustração), `obra`, `autor`, `ano`, `url` (obrigatória quando a fonte for web), `data_acesso`.
* `BlocoLeitura` — `texto`, `pergunta`, `fonte: FonteRef`.
* `ItemCompletar` — `frase_com_lacuna`, `resposta`, `distratores[]`, `fonte: FonteRef`.
* `ParLigar` — `esquerda`, `direita`, `fonte: FonteRef`.
* `AtividadeEntrada` — `tema`, `ano`, `modo` (regular/adaptado), `nivel_suporte` (1–3; a v1 ativa só o 2, que é o padrão quando `modo=adaptado`), `habilidade: HabilidadeCatalogo` (o objeto inteiro, nunca a string do código — o código entra só por consulta ao catálogo, feita pela sessão de redação e confirmada pelo professor; na montagem, o objeto embutido é conferido contra a cópia canônica do catálogo e os textos vêm sempre dela), `confirmado_pelo_professor: bool`, `blocos[]`, `itens_completar[]`, `pares_ligar[]`, `quantidade_questoes` (opcional — controle de volume da folha), `gabarito: bool`, `observacoes_pedagogicas` (opcional, sem dado identificável), `documento_apoio` (opcional — só o registro de que foi consultado, com citação; o arquivo em si não circula pelo pipeline), `respostas_do_professor[]` (registro das perguntas do CUJ 4 e das respostas).

`entrada.py` valida o JSON contra os esquemas e contra o catálogo (códigos, ano, confirmação do professor) antes de qualquer montagem.

**4. Verificador de códigos** (`src/historia_gen/verificador.py`)

Módulo puro: consulta exata por (código, ano) contra o catálogo, sem acesso a modelo, web ou disco além do catálogo. Recusa **código fabricado** — a última linha de defesa antes do `.docx`. A correção semântica da atribuição tema→habilidade não é papel dele (é decisão pedagógica): o mecanismo é a confirmação explícita do professor no passo de redação (CUJ 3), registrada no log.

**5. Montador de formatos e de documento** (`src/historia_gen/formatos.py`, `src/historia_gen/docx_out.py`, `src/historia_gen/template.py`)

* `formatos.py` — determinístico, sem custo de API. Recebe os itens já estruturados e monta: *completar* (frases com lacuna e banco de palavras, sem duplicata ambígua — duplicata é par de itens cujas respostas e distratores se tornam indistinguíveis) e *ligar* (duas colunas embaralhadas por semente parametrizada — aleatória por geração, registrada no log de auditoria; fixa nos testes).
* `template.py` — o template versionado é **código**, não asset binário: constantes nomeadas com valores concretos (`FONTE="Arial"`, `TAMANHO_REGULAR=11..12`, `TAMANHO_ADAPTADO=12..14`, `MARGEM_CM`, `VERSAO_TEMPLATE`) — mudar formato é diff auditável e a versão sobe.
* `docx_out.py` — produz o `.docx` via python-docx: A4 retrato, texto justificado, margens para impressão; **sem cabeçalho** (a única exceção é pedido expresso do professor, e a regra é enunciada sempre com a exceção); sem campos de identificação (escola, professor, turma, aluno, data); sem título genérico — a folha começa pelo conteúdo pedagógico; sem espaços de resposta quando o estudante responde no caderno; citação da fonte no corpo da leitura e nos itens de completar (nos pares de ligar, acompanha o par); marca de rascunho no rodapé + versão do template em metadado; gabarito, quando solicitado, em **arquivo separado** (`<nome>-gabarito.docx`) — nunca na mesma folha; metadados de proveniência apenas nos atributos fixos de `core_properties` do python-docx (título = tema, comentários = versão do catálogo + páginas dos códigos, categoria = versão do template).

**6. Registro de auditoria** (`src/historia_gen/registro.py`)

Um único log append-only, `registros.jsonl`, na pasta de saída — uma linha por geração (padrão de inventário do `drive-audit`: um registro para muitos arquivos): data, tema, ano, modo, habilidade confirmada, hash do `atividade.json`, versão do catálogo, versão do template, semente usada, respostas_do_professor. Nada é impresso na folha do aluno, que não pode ter cabeçalho nem identificação.

### Comandos da CLI (contrato de entrada)

Convenção de ano: string do catálogo (ex.: `"6º ano EF"`). Pasta de saída: `--saida` (padrão `~/Documentos/Escola/Atividades/`, criada se não existir).

```text
python3 -m src.historia_gen montar  <atividade.json> [--saida DIR] [--fonte N]
python3 -m src.historia_gen finalizar <arquivo.docx>          # remove a marca de rascunho e registra a aprovação
python3 -m src.historia_gen verificar <atividade.json>        # roda só as checagens, sem gerar arquivo
python3 -m src.historia_gen catalogo-validar                  # integridade + contagens esperadas + aviso de ano letivo anterior
python3 -m src.historia_gen catalogo-extrair                  # condicional: só depois de Q3 confirmar camada de texto
```

`--fonte N` amplia o corpo do modo adaptado até o limite da faixa (padrão 12; máximo 14). O `finalizar` procura o `registros.jsonl` na pasta do arquivo informado.

Campos de `AtividadeEntrada` preenchidos pelo professor na sessão de redação: tema, ano, modo, nível de suporte, observações pedagógicas, quantidade_questoes (opcional), gabarito, documento_apoio (opcional). Os campos dos formulários do brief que ficam de fora e por quê: `imagens` (v1 sem imagens), `tipo de atividade` (fixado em completar e ligar), `componente` (História, fixo), `páginas máximas` (o número de páginas segue a necessidade de acessibilidade do modo — o controle de volume é `quantidade_questoes`).

### Fluxo de dados

```text
 professor  ──pede──►  SESSÃO DE REDAÇÃO (assistente com web)
                          │  pesquisa fontes citáveis; trata conteúdo ingerido como dado
                          │  escolhe habilidade NO ARQUIVO DO CATÁLOGO
 professor ◄──confirma───┤  o par tema ↔ habilidade (registrado depois no log)
                          │  redige leitura + itens, cada fato com FonteRef
                          ▼
                  atividade.json  (+ respostas_do_professor quando houve CUJ 4)
                          │
                          ▼
 montar (CLI determinística)
   entrada.py      ── esquema + catálogo: código fora do catálogo do ano → recusa a folha inteira
   formatos.py     ── completar e ligar (semente registrada)
   docx_out.py     ── template versionado (sem cabeçalho; rascunho no rodapé; gabarito em arquivo separado)
   registro.py     ── uma linha em registros.jsonl
                          │
                          ▼
 <tema>.docx (+ <tema>-gabarito.docx)
                          │
 professor revisa ──► finalizar  ──► marca removida, aprovação registrada
                          │
                          ▼
                  impressão · Drive pelo processo que o professor já usa (rclone ou cópia manual)
```

### Decisões de arquitetura e por quê

* **Dois passos (redação fora, montagem dentro)** — pesquisa e citação verificáveis exigem acesso à web com ferramenta de busca, que um modelo local não tem; e a redação histórica com fonte correta é a aposta de qualidade mais arriscada do pipeline. Fazer a redação na sessão de assistente que o professor já usa elimina o modelo do caminho crítico: o pipeline fica 100% determinístico (custo zero, testável, falha fechada), e a sessão de redação carrega as garantias de fonte como contrato de saída (`FonteRef` obrigatória por fato, validada na montagem).
* **CLI sobre plataforma** — usuário único não técnico, sensível a custo; o padrão `python3 -m src.drive_audit` é a convenção do repositório.
* **Catálogo fechado sobre extração contínua e sobre banco vetorial** — consulta exata de código tem custo zero, é determinística e auditável (cada código tem página de origem); busca semântica sobre o PDF seria recuperação imprecisa para uma pergunta que é binária (o código existe ou não).
* **Verificação em duas camadas** — recusa de entrada inválida (código fora do catálogo, fato sem fonte, confirmação ausente) acontece na carga; a folha inteira é recusada antes de qualquer arquivo existir. A conferência do professor continua sendo a última checagem, nunca a única.
* **Reuso sem herança de dívida** — o padrão de CLI e o pipeline python-docx são reaproveitados; a entrada de código como texto livre (armadilha do LeituraIA) e a fonte fixa Calibri não são herdados. O padrão de chamada IA do LeituraIA deixa de ser citado como base: com o modelo fora do caminho, não há chamada a adaptar.
* **Template versionado desde o primeiro dia** — o template é código (constantes nomeadas); mudar formato depois quebra o padrão das atividades já impressas, então a versão sobe e o diff é auditável.
* **Entrega por arquivo** — o pipeline grava `.docx` (+ gabarito separado) na pasta local onde o professor já trabalha; a cópia ao Drive segue pelo processo existente. A v1 não cria documentos nativos do Google e não usa nenhuma API de terceiros.
* **Motor comum adiado para a v1.1** — a v1 é o primeiro caso concreto (regular + adaptado); a extração do motor compartilhado acontece quando o segundo tipo de documento (plano de aula, planejamento) chegar, como decidido na ideação (alternativa 10 do brief). O plano já reserva os pontos de extensão: a verificação aritmética do tempo (plano de aula: soma das etapas = duração; planejamento: fechamento de carga horária) e a invocação de atividade como subproduto do plano de aula (etapa 4 da sequência didática do prompt mestre de plano de aula, que exige a atividade completa embutida).

## Risks & Mitigations

| Risco | Mitigação |
|---|---|
| Código de habilidade inventado pelo modelo | Catálogo fechado; verificação exata por (código, ano) na montagem; recusa da folha inteira; código entra por consulta ao catálogo, nunca como texto livre |
| Atribuição tema→habilidade semanticamente errada (código real, habilidade errada) | Confirmação explícita do professor do par antes da geração, registrada no log; habilidade proposta por consulta ao catálogo, não de memória |
| Fonte fabricada ou atribuição errada de trecho | `FonteRef` estruturada obrigatória por fato (obra/autor, URL quando web, data de acesso); folha sem referência é recusada; conferência do professor na revisão. Limite conhecido da v1, registrado: não há checagem automática de existência/atribuição da fonte — é a propriedade 3 com o mecanismo mais fraco dos três, mitigado por registro estruturado + revisão |
| Distorção histórica e infantilização do texto | Instruções de redação com as proibições do prompt mestre (sem simplificação que distorça, sem infantilizar); comparação lado a lado com 3–5 atividades reais adaptadas à mão antes da semana de validação; revisão do professor |
| Injeção de prompt via conteúdo ingerido (web, apostilas de terceiros, documento de apoio) | Regra na sessão de redação: conteúdo ingerido é dado, nunca instrução; toda afirmação factual exige fonte independente do texto ingerido; a saída da sessão é um JSON de esquema fechado que o pipeline valida — instrução embutida que sobreviva vira item de esquema rejeitado ou texto marcado como conteúdo, nunca comando |
| Catálogo obsoleto (SEE-MG atualiza o documento no meio do ano) | Processo anual manual em `fonte_oficial.md` (reconfirmar URL/versão, Q2); `catalogo-validar` avisa quando `data_acesso`/`versao` são do ano letivo anterior — determinístico e offline. Sem checagem online na v1: exigiria baixar e hashear o PDF do site, reabrindo a extração contínua rejeitada na Alternativa C |
| Dado pessoal sensível de aluno (LGPD) | Nenhum campo aceita nome, laudo ou diagnóstico; observações pedagógicas livres não identificáveis; folha sem campo de identificação; na sessão de redação (externa ao pipeline), observações seguem a mesma regra — se um dia um fluxo pedir laudo, é bloqueante e volta à decisão |
| Direito autoral | O documento gerado não copia texto nem reaproveita imagens de obras de terceiros; no máximo uma citação curta, entre aspas, com fonte indicada. O corpus do Drive é usado offline, uma única vez, como modelo de formatação |
| Rede indisponível no dia da aula | Redação é o único passo que exige rede; a montagem é local. Atividade redigida em cima da hora pode ser montada offline |
| Escalabilidade | Limite deliberado: um usuário, uma máquina, sem concorrência. O design não é um serviço; crescer para multiusuário sairia do conceito |
| Perda de rastro de auditoria | `registros.jsonl` append-only por geração; aprovação registrada pelo `finalizar`; catálogo versionado no git (reverter um commit restaura o catálogo anterior) |

--------------------------------------------------------------------------------

## Alternatives Considered

Fonte única: seção "Alternatives Weighed" do brief de ideação (20 itens — 19 rejeitados ou adiados, 1 aceito com condições), transcrita com o motivo de cada decisão.

### Alternativa A: v1 com os três níveis de suporte TEA (1, 2 e 3)

* **Pros**: cobriria de uma vez todo o espectro citado no problema original; evitaria rodadas de expansão posteriores.
* **Cons**: cada nível é praticamente outro produto (outro texto, outros formatos, outra validação pedagógica); triplicaria o volume de casos a testar com um único caso validado à mão.
* **Reason for Rejection**: só o suporte 2 tem receita testada à mão; suporte 1 pode entrar em versão posterior.

### Alternativa B: suporte 3 na v1

* **Pros**: atacaria o caso de maior individualização.
* **Cons**: autoria do material hoje incerta (possivelmente o professor de AEE, não o professor de História); material de suporte 3 tende à comunicação alternativa e a rotinas visuais, que não cabem numa receita única.
* **Reason for Rejection**: decidir só após conversa com a escola/AEE (Open Question Q1).

### Alternativa C: extração automática contínua do documento oficial como pré-requisito da v1

* **Pros**: catálogo sempre atualizado sem trabalho manual anual; eliminaria o passo de revisão humana da extração.
* **Cons**: mecanismo de extração contínua não validado; a v1 precisa do catálogo fechado montado uma única vez, não de um pipeline.
* **Reason for Rejection/Adiamento**: o pipeline automático só se justifica se o processo anual de atualização do catálogo provar ser dor real.

### Alternativa D: imagens geradas por IA, rotuladas como tal

* **Pros**: custo zero e disponibilidade imediata de "ilustrações" para qualquer tema.
* **Cons**: erro de anacronismo frequente em conteúdo histórico; conflito direto com a regra de citar fontes; professor não técnico tende a aceitar o impresso como correto.
* **Reason for Rejection**: imagem de IA nunca é apresentada como documento histórico autêntico (protocolo obrigatório de imagens do brief).

### Alternativa E: banco de imagens de licença livre com citação automática

* **Pros**: resolve licença e citação com material legítimo, priorizando os acervos do protocolo (Wikimedia Commons, Library of Congress, Europeana, Internet Archive).
* **Cons**: adiciona curadoria e um fluxo de verificação a uma v1 que ainda tem premissas por validar.
* **Reason for Adiamento**: versão seguinte, já nascendo sob o protocolo completo de imagens; na v1 o professor insere imagens por conta própria.

### Alternativa F: os cinco formatos da receita-exemplo na v1

* **Pros**: paridade total com a receita manual do 6º ano (que inclui caça-palavras, cruzadinha e labirinto).
* **Cons**: labirinto depende da premissa de imagens; caça-palavras e cruzadinha têm layout de grade difícil de automatizar bem em documento e são montáveis com geradores gratuitos existentes.
* **Reason for Rejection**: v1 fica com texto adaptado + completar + ligar; o professor monta os puzzles que quiser. A divisão de trabalho (modelo gera conteúdo, código monta grade) fica registrada para versão futura.

### Alternativa G: integração com a API do Google Docs para entrega

* **Pros**: documento nativo no ecossistema que o professor já usa; edição colaborativa imediata.
* **Cons**: cadastro de aplicativo, autorização OAuth e manutenção impróprias para usuário único não técnico; o rclone existente já copia arquivos e o Google Docs abre e edita `.docx` normalmente.
* **Reason for Rejection** (na v1): só volta se surgir necessidade real.

### Alternativa H: plataforma web com login e painel

* **Pros**: interface amigável, histórico de materiais, acesso multi-dispositivo.
* **Cons**: infraestrutura, autenticação e manutenção contínua para um usuário único não técnico e sensível a custo.
* **Reason for Rejection**: um fluxo de agente que gera `.docx` basta.

### Alternativa I: começar pela EJA

* **Pros**: dor real do professor no EJA e volume de turmas.
* **Cons**: sem receita validada para adulto; os formatos lúdicos da receita atual arriscam infantilizar, contra a regra pessoal do usuário; não há documento oficial de EJA confirmado no acervo.
* **Reason for Rejection**: validar primeiro onde a receita nasceu (Anos Finais do EF), etapa com fonte oficial confirmada.

### Alternativa J: construir o motor central genérico ("gerador de documentos pedagógicos") na v1

* **Pros**: evitaria retrabalho quando o segundo tipo de documento (plano de aula) chegar.
* **Cons**: com um único caso concreto, qualquer abstração genérica é palpite e tende a gerar retrabalho — abstrair antes do segundo caso é apoiar o motor em um único ponto.
* **Reason for Rejection**: a v1 é o primeiro caso concreto, com etapas naturalmente separáveis (catálogo → conteúdo → documento); a extração do motor comum acontece na v1.1. O Plano Técnico reserva os pontos de extensão.

### Alternativa K: plano de aula e planejamento anual na v1

* **Pros**: dor real, mesma espinha dorsal (História, habilidades oficiais SEE-MG, documento editável), especificação operacional já escrita (prompts mestres de planejamento e plano de aula).
* **Cons**: cada tipo de documento exige o modelo próprio da escola e segundo fluxo de verificação de códigos; incluir na v1 dobraria a validação para um mantenedor único.
* **Reason for Rejection** (na v1): registrados como **v1.1 imediata** — as modalidades que a escola de fato exige primeiro (anual + bimestral/trimestral), com verificação aritmética determinística de carga horária e de distribuição de tempo.

### Alternativa L: registro no diário digital dentro deste conceito

* **Pros**: fecharia o ciclo aula → registro sem intervenção manual.
* **Cons**: escrita em sistema oficial transforma erro do agente em registro escolar formal, de reversão difícil; exigiria credenciais e automação de sistema de governo; quebra a propriedade central do conceito (tudo o que produz é documento que o professor revisa antes do uso).
* **Reason for Rejection**: o domínio já pertence ao agente-grp (Diário GRP de Paracatu/MG, trilha "Integração GRP v2" no roadmap do historiaia-platform). Caminho futuro registrado: este conceito gera o conteúdo como documento; o agente-grp, em versão futura, é quem escreve no diário.

### Alternativa M: começar automatizando tudo

* **Pros**: velocidade percebida; código antes de validação.
* **Cons**: pula a validação mais barata do projeto inteiro.
* **Reason for Rejection**: validar primeiro com protótipo manual (ferramenta de IA genérica + Google Docs seguindo a receita) custa quase nada e responde se a receita generaliza antes de escrever código — validação que corresponde à etapa 1 da ordem de construção do brief (o protótipo manual está na alternativa 13 do brief).

### Alternativa N: tratar o dicionário de habilidades curado à mão (`src/education/enums.py`) como fonte oficial

* **Pros**: já existe no repositório, custo zero, códigos já em uso nos esquemas.
* **Cons**: curado à mão e parcial (cerca de 5–6 códigos por ano, contra as dezenas do documento oficial); sem página de origem nem vínculo com a versão vigente; não é auditável.
* **Reason for Rejection** como fonte: permanece como rascunho e ponto de partida; a única fonte de códigos do projeto é o documento oficial da SEE-MG, via catálogo fechado.

### Alternativa O: busca semântica (banco vetorial) sobre o PDF do currículo

* **Pros**: permitiria consultar por tema, não só por código exato; reutilizaria o Qdrant já presente no monolito.
* **Cons**: recuperação imprecisa para uma pergunta que é binária (o código existe ou não); infraestrutura de índice e manutenção contínuas, contra uma alternativa de custo zero.
* **Reason for Rejection** (na v1): o catálogo fechado responde por consulta exata, sem risco de recuperação imprecisa; busca por tema só se justificaria em fase posterior.

### Alternativa P: apostila na v1

* **Pros**: material consolidado por período/unidade; o conteúdo subjacente já seria produzido pela v1; a compilação em si é montagem determinística sem custo de geração.
* **Cons**: artefato novo (seleção por período, ordenação, capa, numeração, recompilação); custo de desenho e manutenção para usuário único não técnico; risco de descobrir tarde que o formato da escola não é reproduzível em `python-docx`.
* **Reason for Rejection** (na v1): registrada como **v1.x condicionada** a dois requisitos — (a) a escola confirmar o formato próprio de apostila, com o modelo em mãos e reproduzível; (b) uso real da v1 por pelo menos uma unidade. Se entrar: compila só a partir de versões já revisadas e aprovadas, e recompila do zero quando necessário.

### Alternativa Q: vídeos e jogos neste conceito

* **Pros**: engajamento e formatos variados.
* **Cons**: nenhuma das seis lentes de revisão do brief trouxe argumento a favor; um compilado dos `.docx` sem imagem da v1 não carrega mídia sem quebrar as restrições de formato; adicionaria infraestrutura a usuário único sensível a custo.
* **Reason for Rejection**: descartados nesta rodada, com reafirmação na adjudicação final da ideação.

### Alternativa R: corpus de referência do Drive indexado na v1

* **Pros**: consulta direta a apostilas, kits e livros durante a geração.
* **Cons**: exigiria seleção de documentos, construção e consulta de índice por tema e manutenção contínua para usuário único não técnico; o corpus real é grande, heterogêneo, quase todo de terceiros e em meio à reorganização do Drive (`drive-audit/`); indexar antes de curar é indexar material sem verificação de qualidade.
* **Reason for Rejection**: nenhum registro de que a memória do modelo com citação tenha falhado. Propósito correto do corpus registrado na decisão 7 do brief: modelo de formatação, estrutura e ilustração, analisado uma única vez, offline, e destilado no template e na especificação de estilo — sem índice nem busca autônoma em tempo de geração (a leitura pontual de documento indicado pelo professor é a exceção única, coberta por G4); exemplar não é referência de verdade e erro encontrado é registrado, não herdado.

### Alternativa S: corpus indexado comprometido para a versão seguinte

* **Pros**: daria continuidade formal ao item anterior.
* **Cons**: promessa fixa sem gatilho de demanda; perpetua manutenção sem evidência de uso.
* **Reason for Rejection** como promessa: registrada como **expansão condicionada** — só se o uso real mostrar demanda repetida pelos mesmos documentos. Um índice em tempo de geração segue rejeitado; a restrição de direito autoral vale desde o primeiro dia.

### Alternativa T: atividade para alunos regulares na v1

* **Pros**: é o artefato-base da rotina real do professor (criar a da turma, depois adaptar); motor idêntico (tema + ano + catálogo SEE-MG → `.docx`); custo marginal pequeno; infraestrutura totalmente compartilhada com o modo adaptado.
* **Cons**: sem especificação de estilo própria, seria uma aproximação — o risco de o "regular" sair genérico.
* **Reason for Acceptance (com condições — única aceita das vinte)**: aceita na v1 com duas condições — especificação de estilo própria (encerrada pelo prompt mestre regular do brief) e os mesmos dois formatos da v1 (ampliar o cardápio, incluindo as objetivas `a–d` e discursivas do prompt mestre, é outra expansão, julgada por si). A dor que motiva o projeto continua sendo a adaptação manual: o modo regular não substitui o modo adaptado como foco.

--------------------------------------------------------------------------------

## Non-Functional Requirements

* **Privacidade (LGPD — Lei Geral de Proteção de Dados)**: a ferramenta não recebe nome de aluno, laudo nem diagnóstico. A entrada aceita nível de suporte e observações pedagógicas livres; a folha gerada não tem campo de identificação nenhum. Na sessão de redação, que é externa ao pipeline, as observações seguem a mesma regra — dado identificável de aluno não entra em nenhum campo do `atividade.json`. Se algum fluxo futuro pedir upload de laudo, o fluxo é tratado como bloqueante e a decisão volta à pauta — laudo é dado sensível e enviá-lo a serviço de IA exigiria base legal específica.
* **Propriedade intelectual**: o documento gerado não copia texto nem reaproveita imagens de obras de terceiros; no máximo uma citação curta, entre aspas, com fonte indicada. O corpus do Drive é usado offline, uma única vez, como modelo de formatação — nunca reproduzido. Vale desde o primeiro dia porque a atividade é impressa e distribuída na escola.
* **Custo**: o pipeline de montagem tem custo zero — sem modelo, sem API, tudo local. A redação usa a sessão de assistente que o professor já utiliza e paga de todo modo; o design não adiciona custo. O catálogo é montado uma única vez e reprocessado uma vez por ano, quando o documento oficial atualizar.
* **Auditoria**: cada geração acrescenta uma linha ao `registros.jsonl` (tema, habilidade confirmada, versões, semente, respostas do professor, hash da entrada); o `.docx` carrega nos metadados fixos a versão do catálogo, as páginas de origem dos códigos e a versão do template; o catálogo registra data de acesso e os dois hashes do PDF oficial. Sem esse registro, a regra "código nunca inventado" não é verificável.
* **Falha fechada**: o pipeline recusa a saída — entrada fora do esquema, código fora do catálogo do ano, fato sem `FonteRef`, confirmação do professor ausente — sempre com a lista dos itens reprovados. Na sessão de redação, fonte sem evidência citável não entra no material. O vazio nunca é preenchido com valor inventado.
* **Rollback**: sem migração e sem estado — o catálogo é versionado no git (reverter um commit restaura o catálogo anterior); as atividades geradas são arquivos soltos que o professor apaga.

## Additional Resources

* [agente-atividades-adaptadas-historia.md](agente-atividades-adaptadas-historia.md) — brief de ideação (predecessor deste design; prompts mestres e protocolo de imagens completos)
* `/home/flavio/drive-audit/inventory.csv` — inventário do Drive com o PDF oficial do CRMG (MD5 `123289db…`) e as atividades adaptadas reais feitas à mão (régua de comparação do plano de validação)
* `Projetos/leituraia/generator.py` — referência do padrão de chamada IA do repositório (não reutilizado na v1: o modelo saiu do caminho; a armadilha da entrada de código como texto livre segue registrada)
* `src/education/schemas.py`, `src/education/enums.py` — esquemas e dicionário rascunho (não modificados)
* `scripts/standardize_fonts.py` — pipeline python-docx existente (Calibri fixa — não modificado; prova de que a biblioteca funciona no ambiente)
* `src/api/v2/chat_coraci.py` — configuração do Ollama local já em uso (candidato a fluxo offline em versão futura; fora do caminho da v1)
* `/home/flavio/Desktop/Projetos/audit-2026-09/historiaia-platform/ROADMAP_EXECUTIVO.md` — trilha "Integração GRP v2" do agente-grp (domínio do diário digital)

## Future Improvements

* **v1.1 (imediata, mesma espinha dorsal)**: plano de aula e planejamento anual/bimestral, com as especificações já escritas (prompts mestres), verificação aritmética determinística (soma do tempo = duração; fechamento de carga horária) e extração do motor comum.
* **v1.x (condicionada)**: apostila — só com modelo da escola confirmado e uso real de uma unidade; compila só de versões aprovadas.
* **Expansão por perfil**: cada perfil da taxonomia completa (módulos combináveis) é ativado depois de testar a especificação contra atividades reais adaptadas à mão daquele perfil.
* **Expansão de formatos**: objetivas com alternativas `a–d` e discursivas do prompt mestre regular, com montador próprio.
* **Imagens**: versão seguinte nasce sob o protocolo completo de imagens do brief (fontes priorizadas, verificação de licença, legenda fixa, rotulagem, auditoria).
* **Puzzles com grade**: modelo gera conteúdo (palavras, pistas, pares); gerador programático monta grade como tabela.
* **Índice do corpus**: só se o uso real mostrar demanda repetida pelos mesmos documentos.
* **Fluxo offline de adaptação**: o Ollama local (`src/api/v2/chat_coraci.py`) como opção de redação sem rede, com os mesmos contratos de `FonteRef` — só se o uso real mostrar que a sessão com web não basta.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

> **Decisões tomadas nesta redação** (o autor delegou as escolhas; critério adotado em cada caso: a alternativa que mais automatiza sem ampliar o recorte da v1 nem violar as restrições de custo e privacidade — cada uma reversível no review):
>
> * **D1 — Catálogo em JSON versionado** (e não CSV): diffável no git, validável por esquema, com os dois hashes e a página de origem por habilidade.
> * **D2 — Extração assistida do PDF com página citada**: produz rascunho do catálogo que passa por revisão manual obrigatória — a revisão humana do catálogo fechado é um limite imposto pelo brief e não será automatizada. O item é **condicional a Q3** (camada de texto); sem camada de texto, o catálogo é digitado manualmente a partir do esquema do JSON, e a ferramenta de extração não entra.
> * **D3 — Redação fora do pipeline** (decisão do review, substitui a D3 original "Ollama como único caminho"): a pesquisa e a redação acontecem na sessão de assistente com web que o professor já usa, sob o contrato de saída `FonteRef` validado na montagem. Subir para uma API paga dentro do pipeline violaria uma propriedade do conceito — não é mera escolha técnica; e um modelo local sem acesso web não cumpre a regra de fontes citáveis.
> * **D4 — CLI no padrão `python3 -m src.historia_gen`** com subcomandos `montar`, `finalizar`, `verificar`, `catalogo-validar` e `catalogo-extrair` (condicional) — segue a convenção já adotada em `src/drive_audit`.
> * **D5 — Instruções de redação como arquivos versionados** em `src/historia_gen/prompts/` (pesquisa.md; seções de adaptação do prompt mestre adaptado): o comportamento da sessão de redação torna-se um diff auditável e uma fonte única e autoritativa. Na v1, o prompt adaptado entra só com a seção do suporte 2; os módulos dos demais perfis são acrescentados quando cada perfil for ativado — a estrutura combinável completa entra na expansão por perfil, não aqui.
> * **D6 — Proveniência em um log único**: metadados fixos do `.docx` + `registros.jsonl` append-only (um registro para muitas gerações, padrão do `drive-audit`) — sem JSON irmão por documento. As respostas do professor moram no `atividade.json` de origem e são copiadas para a linha do log.
> * **D7 — Gabarito em arquivo separado e aprovação comandada**: `<tema>-gabarito.docx` nunca na mesma folha; `finalizar` remove a marca de rascunho e registra a aprovação no log, preservando a versão do template nos metadados.

### Reconciliação com o brief

A seguir, a comparação entre este draft e o predecessor (`docs/designs/agente-atividades-adaptadas-historia.md`). Nenhuma divergência fica sem registro; as decisões abaixo foram tomadas por delegação do autor, pelo critério registrado no bloco D1–D7, e são reversíveis no review.

* **Contradição 1 — "reusando o gerador e os esquemas existentes" (brief, ordem de construção, etapa 4) vs. esquemas novos neste design.** O design cria `src/historia_gen/modelos.py`. **Decisão**: manter — os esquemas existentes aceitam código BNCC/CRMG como texto livre, exatamente a armadilha que a decisão 2 do brief proíbe herdar; o reuso se realiza como padrão de CLI + infraestrutura compartilhada (python-docx, inventário, rclone), com `src/education/` e `Projetos/leituraia/` intocados.
* **Contradição 2 — "salva onde o professor já trabalha (Drive)" (brief, Goals) vs. pasta local fixa neste design.** O design fixa a saída em `~/Documentos/Escola/Atividades/` e a cópia ao Drive acontece pelo processo que o professor já usa (rclone ou cópia manual); o pipeline não invoca rclone na v1. **Decisão**: manter — entrega por arquivo é a decisão 5 do brief, e a pasta local é onde o pipeline de fontes do professor já opera (`scripts/standardize_fonts.py`); o caminho até o Drive não é integração nova.
* **Adição 1 — dependências novas** (detalhadas no item 19): `python-docx` nas dependências principais; `pdfplumber` no extra `dev`, condicionado a Q3. O brief não escolheu bibliotecas; isto muda o manifesto do projeto.
* **Adição 2 — CLI `python3 -m src.historia_gen` com subcomandos e instruções de redação como arquivos versionados** (`prompts/`). O brief rejeitou plataforma web e pediu fluxo de agente, mas não fixou a interface nem o local das instruções; isto define a interface externa.
* **Adição 3 — `registros.jsonl` único + metadados fixos do `.docx`** como mecanismo de proveniência. O brief exigiu o registro da origem dos códigos (decisão 2) sem definir onde ele vive; a restrição de folha sem cabeçalho/identificação impede imprimi-lo na folha.
* **Adição 4 — o PDF oficial do CRMG versionado no repositório** (`catalogo/dados/fonte_oficial/`), documento público de ~9 MB, para tornar a checagem de integridade offline e dar ao extrator o arquivo que ele lê.
* **Omissão corrigida**: a "fundamentação sob demanda" (professor indica documento de apoio; a redação lê trechos naquela geração e cita a fonte) estava presente no brief (Goals) e faltava no primeiro draft — incorporada em G4 e na sessão de redação.
* **Divergência assumida no pós-review**: o campo `quantidade_questoes` dos formulários do brief, ausente do primeiro draft, voltou como entrada opcional (M7); e o Ollama saiu do caminho da v1 (D3) — o brief o citava como infra de custo zero, mas o review mostrou que um modelo local sem acesso web não sustenta a regra de fontes citáveis; ele permanece registrado como candidato a fluxo offline futuro.

### Fases e pré-condições

O sequenciamento abaixo substitui a referência externa à "ordem de construção" do brief; cada fase termina com o repositório estável e testável.

| Fase | Entrega | Pré-condição | Critério de saída |
|---|---|---|---|
| **0 — Validações baratas** | `fonte_oficial.md` preenchido: URL e versão vigentes (Q2), teste de copiar e colar (Q3), existência de documentos de EM/EJA (Q4), conversa com escola/AEE (Q1), linha de base cronometrada (Q5) | — | Q2 e Q3 respondidas; Q5 medida |
| **1 — Catálogo** | PDF oficial versionado; `catalogo_crmg_ef_anos_finais.json` montado (extração assistida ou digitação, conforme Q3) e revisado à mão; contagens esperadas por ano em `fonte_oficial.md`; `catalogo-validar` e seus testes | Q2 fechada; Q3 decide a ferramenta | `catalogo-validar` passa (integridade, contagens, hashes) |
| **2 — Verificador** | `verificador.py` + testes, incluindo os adversários | Fase 1 | Código fora do catálogo reprova; consulta exata confirmada |
| **3 — Montagem** | `modelos.py`, `entrada.py`, `formatos.py`, `template.py`, `docx_out.py`, `registro.py`, `finalizar`; primeiro `.docx` do **modo adaptado** (a receita validada), depois o regular (condição da Alternativa T) | Fase 2 | Folha gerada passa nas regras do template; recusas de entrada cobertas por teste |
| **4 — Validação comparativa** | Gerar os mesmos temas de 3–5 atividades reais adaptadas à mão (inventário do Drive) e comparar lado a lado com o material do agente | Fase 3 | Professor valida fidelidade pedagógica da comparação |
| **5 — Medição em semana real** | Tempo e aceitação medidos contra a linha de base | Q5 fechada; Fase 4 aprovada | Critério do G7; só então expansões entram na pauta |

### Target Files to Create/Modify

#### 1. `src/historia_gen/__init__.py` (Create)

* **Type / Scope**: pacote Python.
* **Proposed Changes**: declaração do pacote e metadados (versão do template `.docx` como constante, importada por `template.py`).

#### 2. `src/historia_gen/__main__.py` (Create)

* **Type / Scope**: CLI (entry point `python3 -m src.historia_gen`).
* **Proposed Changes**: cinco subcomandos — `montar <atividade.json> [--saida DIR] [--fonte N]` (saída padrão `~/Documentos/Escola/Atividades/`, criada se não existir; `--fonte` amplia o corpo do modo adaptado até 14), `finalizar <arquivo.docx>` (log na pasta do arquivo informado), `verificar <atividade.json>`, `catalogo-validar`, `catalogo-extrair` (condicional a Q3; import de `pdfplumber` preguiçoso, dentro do subcomando, para não quebrar `montar` em instalação sem o extra dev). Erros de validação saem com código de retorno não zero e a lista dos itens reprovados. O pipeline nunca pergunta no meio da execução — a única interação humana planejada é a confirmação do par tema↔habilidade, que acontece na sessão de redação e chega pronta no JSON.

#### 3. `src/historia_gen/modelos.py` (Create)

* **Type / Scope**: schemas Pydantic — o contrato entre redação e montagem.
* **Proposed Changes**: `HabilidadeCatalogo` (código, descrição literal, ano, unidade temática, objeto de conhecimento, página), `MetaCatalogo` (documento, URL oficial, versão, data de acesso, `pdf_md5` de 32 hex, `pdf_sha256` de 64 hex, revisão aprovada), `FonteRef`, `BlocoLeitura`, `ItemCompletar`, `ParLigar`, `AtividadeEntrada` (inclui `nivel_suporte` e `quantidade_questoes`), `Reprovacao` (campo, motivo) — conforme especificado no componente 3 do Plano Técnico. O código de habilidade nunca entra como texto livre: o campo é o objeto `HabilidadeCatalogo` inteiro, resultado da consulta ao catálogo, com a confirmação do professor registrada.

#### 4. `src/historia_gen/catalogo/__init__.py` + `src/historia_gen/catalogo/carregar.py` (Create)

* **Type / Scope**: carga e validação estrutural do catálogo.
* **Proposed Changes**: carrega o JSON, valida contra `MetaCatalogo`/`HabilidadeCatalogo`, recalcula os dois hashes do PDF versionado em `dados/fonte_oficial/` e recusa catálogo sem revisão aprovada ou com hash divergente do registrado; expõe a consulta exata por (código, ano).

#### 5. `src/historia_gen/catalogo/dados/catalogo_crmg_ef_anos_finais.json` (Create)

* **Type / Scope**: dados versionados — o catálogo fechado.
* **Proposed Changes**: todas as habilidades de História dos Anos Finais do EF, literais do documento oficial, com página de origem; `meta` com URL oficial, versão, data de acesso e os dois hashes. Montado na Fase 1 e revisado à mão; passa a ser a única fonte de códigos do projeto.

#### 6. `src/historia_gen/catalogo/dados/fonte_oficial/crmg_infantil_ef.pdf` + `src/historia_gen/catalogo/fonte_oficial.md` (Create)

* **Type / Scope**: o documento oficial versionado e o registro de proveniência.
* **Proposed Changes**: cópia do PDF público da SEE-MG (~9 MB) commitada ao lado do catálogo — torna a checagem de hash offline e dá ao extrator (quando Q3 permitir) o arquivo que ele lê. O `fonte_oficial.md` registra: URL da página da SEE-MG, versão vigente, data de confirmação, os dois hashes, o resultado do teste de camada de texto (Q3), a nota sobre documentos oficiais de EM/EJA (Q4), a **contagem esperada de habilidades por ano** (contraprova contra catálogo truncado) e o processo anual de reconfirmação. Atualizado uma vez por ano.

#### 7. `src/historia_gen/catalogo/extraidor.py` (Create — condicional a Q3)

* **Type / Scope**: extração assistida (roda cerca de uma vez por ano).
* **Proposed Changes**: lê o PDF versionado página a página (`pdfplumber`, import preguiçoso), emite rascunho do catálogo com página de origem por habilidade; marca `revisao_aprovada=false` até a revisão manual. Se o PDF não tiver camada de texto (Q3), este arquivo não entra e o catálogo é digitado manualmente a partir do esquema do JSON.

#### 8. `src/historia_gen/verificador.py` (Create)

* **Type / Scope**: módulo puro de verificação.
* **Proposed Changes**: consulta exata por (código, ano) contra o catálogo; função de validação de folha que retorna a lista de `Reprovacao`; nenhum acesso a modelo, web ou disco além do catálogo. A checagem adversária de tema fora do ano/série pertence ao **fluxo** (`entrada.py` recusa entrada cuja habilidade é de outro ano e cuja confirmação do professor está ausente) — o módulo puro permanece consulta de códigos.

#### 9. `src/historia_gen/entrada.py` (Create)

* **Type / Scope**: carga e validação do `atividade.json`.
* **Proposed Changes**: valida o JSON contra os esquemas de `modelos.py`; valida a habilidade contra o catálogo (existência, ano, `confirmado_pelo_professor=true`); valida que cada `BlocoLeitura`, `ItemCompletar` e `ParLigar` tem `FonteRef` completa (obra/autor; URL obrigatória quando `tipo` indica fonte web; `data_acesso`); produz a lista de `Reprovacao` que recusa a montagem.

#### 10. `src/historia_gen/prompts/pesquisa.md` + `src/historia_gen/prompts/adaptado_suporte2.md` (Create)

* **Type / Scope**: instruções versionadas da sessão de redação.
* **Proposed Changes**: `pesquisa.md` — transposição operacional do prompt mestre regular (9 seções) mais as regras de segurança (conteúdo ingerido é dado; toda afirmação factual exige fonte independente do texto ingerido; escolha da habilidade por consulta ao arquivo do catálogo, com confirmação do professor; gatilhos legítimos de pergunta do CUJ 4; saída no esquema de `modelos.py`). `adaptado_suporte2.md` — a receita validada do suporte 2 (blocos curtos, uma pergunta imediatamente após cada bloco) e as regras do prompt mestre adaptado aplicáveis ao suporte 2; os módulos dos demais perfis entram quando cada perfil for ativado.

#### 11. `src/historia_gen/formatos.py` (Create)

* **Type / Scope**: montador determinístico de formatos.
* **Proposed Changes**: `completar` (frases com lacuna e banco de palavras, sem duplicata ambígua) e `ligar` (duas colunas embaralhadas por semente parametrizada — aleatória por geração, registrada no log; fixa nos testes). Recebe as estruturas de `modelos.py`; produz estruturas de tabela para o montador `.docx`; sem custo de API.

#### 12. `src/historia_gen/template.py` (Create)

* **Type / Scope**: o template versionado como código.
* **Proposed Changes**: constantes nomeadas com valores concretos — `FONTE = "Arial"`; `TAMANHO_REGULAR = 11` (faixa aceita 11–12); `TAMANHO_ADAPTADO = 12` (faixa aceita 12–14; `--fonte` aumenta até o limite); `MARGEM_CM = 2.0`; `VERSAO_TEMPLATE` (importada de `__init__.py`). Mudança de formato = diff auditável + incremento de versão.

#### 13. `src/historia_gen/docx_out.py` (Create)

* **Type / Scope**: montador `.docx` (python-docx).
* **Proposed Changes**, um item por regra:
  * A4 retrato; fonte e corpo conforme `template.py`; texto justificado; margens para impressão.
  * Sem cabeçalho (única exceção: pedido expresso do professor — regra enunciada sempre com a exceção).
  * Sem campos de identificação (escola, professor, turma, aluno, data); sem título genérico; a folha começa pelo conteúdo pedagógico.
  * Sem espaços ou linhas de resposta quando o estudante responde no caderno.
  * Citação da `FonteRef` no corpo da leitura e nos itens de completar; nos pares de ligar, a referência acompanha o par.
  * Marca de rascunho no rodapé; versão do template em metadado (permanece após o `finalizar`).
  * Gabarito em arquivo separado (`<tema>-gabarito.docx`) quando `gabarito: true`.
  * Metadados de proveniência apenas nos atributos fixos de `core_properties` (título = tema; comentários = versão do catálogo + páginas dos códigos; categoria = versão do template) — nenhuma propriedade customizada.
  * Estilo de impressão do modo adaptado: sem grandes áreas de tinta (o montador não emite preenchimentos), contraste adequado.

#### 14. `src/historia_gen/registro.py` (Create)

* **Type / Scope**: log de auditoria append-only.
* **Proposed Changes**: acrescenta uma linha ao `registros.jsonl` da pasta de saída por geração: data, tema, ano, modo, habilidade confirmada, hash do `atividade.json`, versão do catálogo, versão do template, semente, `respostas_do_professor`. O `finalizar` acrescenta a linha de aprovação (arquivo, data). Padrão de inventário do `drive-audit`: um registro para muitas gerações.

#### 15. `tests/test_historia_gen_verificador.py` (Create)

* **Type / Scope**: testes unitários do verificador e da entrada.
* **Proposed Changes**: consulta exata positiva; código inexistente reprovado; folha com um código inválido é recusada inteira, com a lista de `Reprovacao`; **testes adversários de fluxo** — habilidade de outro ano recusada por `entrada.py`; confirmação do professor ausente recusa a montagem; fato sem `FonteRef` recusa a montagem.

#### 16. `tests/test_historia_gen_catalogo.py` (Create)

* **Type / Scope**: testes de integridade e completeza do catálogo.
* **Proposed Changes**: esquema válido; códigos únicos; campos obrigatórios presentes (página, versão, os dois hashes); `revisao_aprovada=true` exigido para uso; recusa de catálogo com hash divergente; **asserção de completeza** — contagem de habilidades por ano igual à documentada em `fonte_oficial.md`.

#### 17. `tests/test_historia_gen_docx.py` (Create)

* **Type / Scope**: testes das regras de formato do documento e dos formatos.
* **Proposed Changes**: para os dois modos — ausência de cabeçalho e de campos de identificação; marca de rascunho no rodapé; fonte e corpo conforme as constantes de `template.py` (faixas 11–12 e 12–14); texto justificado; gabarito em arquivo separado quando solicitado; metadados fixos gravados; após `finalizar`, marca ausente e aprovação no log. Em `formatos`: mesma semente produz o mesmo layout; sementes diferentes produzem layouts (em geral) diferentes; banco de palavras sem duplicata ambígua; pares de ligar balanceados.

#### 18. `tests/test_historia_gen_cli.py` (Create)

* **Type / Scope**: smoke da CLI.
* **Proposed Changes**: `--help` dos cinco subcomandos; `catalogo-validar` sobre o catálogo versionado (passa) e sobre catálogo adulterado em fixture (falha com retorno não zero); `montar` com entrada de exemplo do repositório; `finalizar` sobre arquivo de teste.

#### 19. `pyproject.toml` (Modify)

* **Type / Scope**: configuração do projeto.
* **Proposed Changes**: `python-docx` nas **dependências principais** (o pacote roda fora de dev; hoje ele é importado só por `scripts/standardize_fonts.py` e não está declarado em lugar nenhum); `pdfplumber` no extra `dev`, **condicionado a Q3** (se o PDF não tiver camada de texto, a dependência não entra). Nenhuma outra dependência: o pipeline não usa httpx nem cliente de modelo.

#### 20. `docs/designs/SITEMAP.md` (Modify)

* **Type / Scope**: índice dos designs.
* **Proposed Changes**: atualizar o status da linha existente deste design quando ele for aprovado (a linha já existe; nenhuma duplicata).

#### 21. `CHANGELOG.md` (Modify)

* **Type / Scope**: changelog do repositório.
* **Proposed Changes**: entrada em `[Não publicado]` descrevendo a v1 do agente (pacote, CLI, catálogo, verificador, template) quando a implementação for incorporada.

#### 22. `docs/historia_gen/validacoes.md` (Create)

* **Type / Scope**: documento vivo de validações.
* **Proposed Changes**: registra as cinco Open Questions com resultado e data — conversa com escola/AEE, versão vigente confirmada com URL, teste de camada de texto, documentos de EM/EJA, linha de base cronometrada — e, depois, a comparação com as atividades reais (Fase 4) e a medição da semana real de aulas (Fase 5). É pré-condição para qualquer ampliação de escopo.

**Arquivos deliberadamente não modificados:** `src/education/enums.py` e `src/education/schemas.py` (o dicionário vira rascunho histórico; os esquemas novos vivem em `src/historia_gen/modelos.py` para não acoplar o domínio educacional do monolito ao fluxo do agente); `scripts/standardize_fonts.py` (ferramenta de manutenção de arquivos existentes; a Calibri fixa é o comportamento atual desejado); `Projetos/leituraia/` (a referência do padrão de chamada IA deixa de ser citada como base — o modelo saiu do caminho da v1); `src/api/v2/chat_coraci.py` (a configuração Ollama não é importada pela CLI — importá-la arrastaria FastAPI e o contrato do Coraci; ela permanece como candidato futuro documentado).

### Verification Plan

* **Lint e checagem de tipos**: `ruff check src/historia_gen tests` e `ruff format --check src/historia_gen tests` (o formato é verificação da matriz do repositório e cobre `src` e `tests`); `mypy src/historia_gen` (a checagem de tipos do repositório cobre o código, não os testes).
* **Testes unitários**: a suíte do monolito (`pytest tests/`) apanha os novos arquivos automaticamente; para rodar só o pacote, `pytest tests/test_historia_gen_*.py` diretamente (o `--only` de `scripts/test_all.sh` filtra por `projeto:verificação`, não por arquivo de teste).
* **Cobertura**: o gate do repositório é global (`--cov=ai --cov=api --cov=src --cov-fail-under=70` via `PYTEST_ADDOPTS` no `ci.yml`) — o pacote novo entra no denominador do monolito inteiro, e os módulos dele são todos testáveis por serem determinísticos (a sessão de redação, que não é testável, está fora do repositório e fora do gate). Meta do pacote: cobertura acima do gate global.
* **Gates adversários obrigatórios** (critérios de aceite das Fases 2 e 3): código fora do catálogo reprova a folha; habilidade de outro ano recusa a entrada; confirmação do professor ausente recusa a montagem; fato sem `FonteRef` recusa a montagem; catálogo truncado falha na asserção de completeza.
* **Validação manual do documento** (Fase 3→4): gerar 1 atividade adaptada e 1 regular com tema real (ex.: Roma Antiga, 6º ano); conferir a impressão A4, a ausência de cabeçalho e de campos de identificação e a marca de rascunho no rodapé; conferir cada código impresso contra o documento oficial (a conferência do professor é a última checagem, nunca a única); comparar lado a lado com 3–5 atividades reais adaptadas à mão (inventário do Drive) para os mesmos temas — a régua de fidelidade pedagógica antes da semana real.
* **Aceitação (Fase 5)**: critério objetivo do G7 — tempo do fluxo ≤ 50% da linha de base medida (Q5) e aceitação sem retrabalho de formatação em ≥ 4 de 5 atividades. Só depois dessa medição qualquer expansão é retomada.

*Drafted with EGM*
