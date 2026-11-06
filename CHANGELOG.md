# Changelog

Todas as mudanças relevantes deste projeto são registradas neste arquivo.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
versionamento segue o [SemVer](https://semver.org/lang/pt-BR/). A versão corrente
é a declarada em `pyproject.toml` (`2.1.1`).

## [Não publicado]

### Adicionado

- `src/drive_audit/`: auditoria do Google Drive (rclone) — inventário,
  detecção transitiva de pastas vazias e de duplicatas por hash, plano de
  renomeação arquivística e `apply` de lixeira em dry-run por padrão
  (`python3 -m src.drive_audit inventory|analyze|apply`).
- `apply --lote <csv>`: aplica apenas o lote aprovado, em vez do
  `duplicates.csv` inteiro.
- `Projetos/next-app`, `Projetos/web` e `Projetos/leituraia` versionados: os
  caminhos exigidos pelo `projects-ci.yml` existiam apenas no disco, e os 4 jobs
  falhavam com "working directory not found".
- `tests/shell/test_scripts_smoke.bats`: 5 testes bats cobrindo os 15 scripts
  shell versionados (existência, `bash -n`, shebang, `--help` e convenção de
  nomes de arquivo).
- `tests/test_core_config.py`: testes de `src/core/config.py` — defaults,
  override por variável de ambiente e a guarda que impede subir em produção com
  o segredo JWT padrão.
- `scripts/test_all.sh`: matriz única de testes dos sete projetos, com
  `--only`/`--skip` por projeto ou por verificação (ex.:
  `--only monolito:ruff-check`), `--fast`, `--verbose` e resumo por projeto.
- `.dockerignore` em allowlist, para o contexto de build da imagem não incluir
  segredos nem o repositório inteiro.
- Documentação comunitária: `SECURITY.md` (divulgação responsável) e
  `.github/dependabot.yml` (atualizações semanais de `pip`, `npm`, `docker` e
  GitHub Actions).
- `src/historia_gen/`: agente gerador de atividades de História (v1 — modos
  regular e TEA suporte 2, Anos Finais do EF), em dois passos. A redação fica
  na sessão de assistente com web (`prompts/pesquisa.md` e
  `prompts/adaptado_suporte2.md`) e grava `atividade.json` com fonte
  estruturada por fato; a montagem é um pipeline determinístico de custo zero
  (`python3 -m src.historia_gen montar|finalizar|verificar|catalogo-validar|catalogo-extrair`)
  que valida o código contra o catálogo fechado do CRMG, recusa a folha com
  problema e monta o `.docx` (Arial, justificado, sem cabeçalho, rascunho no
  rodapé, gabarito em arquivo separado). Inclui o catálogo versionado com as 97
  habilidades de História dos Anos Finais (com página de origem e os dois
  hashes do PDF oficial), o extrator assistido anual e o log de auditoria
  `registros.jsonl`.
- `src/historia_gen` (template 1.3): itens de **parear iguais**, **ordenação** e
  **figura de apoio** (PNG/JPEG local, 14 cm centralizada, com legenda e
  citação) — as lacunas de resposta de baixa exigência que a Fase 4 apontou. A
  validação de entrada recusa imagem ausente ou em formato não aceito e resolve
  caminho relativo a partir da pasta do `atividade.json`; a grade do professor
  passou a listar todos os itens impressos (marcar, V/F, parear e ordenar) e o
  log registra a contagem por formato. O caça-palavras fica fora por decisão do
  design aprovado (Alternativa F).
- `src/historia_gen` (template 1.4): `catalogo-conferir`, que relê a camada de
  texto do PDF oficial e confronta as 97 linhas (código, descrição, unidade,
  objeto e página), com `--aprovar --responsavel` gravando `revisado_por`,
  `revisao_metodo` e `revisao_data` no `meta` — o gate `revisao_aprovada` deixou
  de depender de edição manual do JSON e o catálogo versionado está aprovado
  (97/97, 2026-11-03).
- `src/historia_gen` (template 1.8): **ficha de planejamento do professor**
  (GAP-2 residual da Fase 4). `planejamento` opcional — objetivo, duração,
  metodologia, recursos e público/PDI — entra no topo da página do professor, num
  bloco único, antes do "como aplicar"; só os campos preenchidos são impressos e
  o campo exige `registro_mediacao: true` (sem a página, a ficha não teria onde
  sair e a entrada é recusada). Com a ficha, a caixa de observações cede 1,4 cm
  para a página continuar fechando em uma folha: medido no exemplo de 13 itens
  (LibreOffice + pymupdf), a folha do professor termina a 27,1 cm dos 27,7 cm
  úteis, em 3 páginas (2 do estudante + a do professor).
- `src/historia_gen` (template 1.9): **caixa de vocabulário** no topo da folha
  (GAP-6 da Fase 4). `vocabulario` opcional (até 8 palavras-chave) abre a folha
  do estudante com o rótulo em negrito, como no caderno de referência adaptado à
  mão; no suporte 3 a caixa volta em cada tarefa, ao lado do banco de palavras,
  porque a página anterior já foi recolhida. Medido no exemplo versionado com 13
  itens, ficha e vocabulário: a primeira página termina a 26,3 cm dos 27,7 cm
  úteis e a folha continua em 3 páginas; no suporte 3 (8 tarefas) a caixa ocupa
  0,5 cm por página e o total segue em 8 páginas.
- `tempo-manual`: registro da linha de base da Q5 (minutos de uma adaptação feita
  à mão, em `docs/historia_gen/q5-linha-de-base.csv`) e comparação fail-closed
  com a mediana de `duracao_s` do `registros.jsonl`.
- `tempo-formulario`: formulário impresso da Q5 em
  `docs/historia_gen/q5-formulario.docx` — uma página por medição (padrão 2
  vias), com a identificação da adaptação, a grade de tempo por etapa do
  protocolo (início, fim, minutos) com o total em destaque, o campo de
  retrabalho e o comando que registra o número; o professor deixa de cronometrar
  em papel avulso.
- `scripts/verificar_impressao_figura.py`: mede a figura de apoio no PDF impresso
  (LibreOffice + pymupdf) nas proporções larga, quadrada e retrato.

### Alterado

- `docs/historia_gen/`: **quarto par da Fase 4** (7º ano, Grandes Navegações e
  Reforma) — avaliação adaptada do Drive contra folha gerada com `EF07HI05X`,
  ficha de planejamento e caixa de vocabulário. O comparativo passa a ter quatro
  pares; o par confirma GAP-2/GAP-5 no 7º ano e registra a pendência de redação
  (16,7 palavras por frase contra 9,9 do baseline).
- `src/historia_gen` (template 1.7): **GAP-7 — uma tarefa por página no suporte
  adaptado**. `nivel_suporte: 3` (só no modo adaptado) monta a folha com **uma
  tarefa por página**: cada bloco de leitura e cada item começam em página nova e
  a página repete a instrução, o banco de palavras e a linha de fontes, porque é
  entregue e recolhida sozinha. A folha da fixture com 7 tarefas sai em 7 páginas
  (+ a do professor), contra 1 página do suporte 2. O suporte 2 não mudou —
  conferido comparando o `.docx` gerado antes e depois da refatoração: mesmos
  parágrafos, mesmas tabelas e mesmas quebras de página (só a ordem sorteada
  muda, porque a semente é aleatória a cada `montar`). A validação de entrada
  passou a aceitar 3 no adaptado e a recusar 1 e o 3 no regular.
- `src/historia_gen` (template 1.6), revisão de impressão da atividade de Roma
  Antiga **com figura real** (mapa do Império em 117 d.C., domínio público): a
  página de registro do professor saía numa quinta página 95% vazia, com o campo
  de observações sozinho, porque a grade por item chegava ao pé da folha. A
  coluna do item passou a 8,6 cm (as três de marcação a 2,7/2,8/2,7 cm), o
  rótulo do item é resumido em 46 caracteres, a lista "Como aplicar" usa respiro
  de 4 pt, o rótulo de observações cola na caixa e a linha de data/tempo tem
  1,0 cm de altura para escrita à mão. Resultado medido no PDF (LibreOffice +
  pymupdf): a folha do estudante fica em 3 páginas (26,6 / 26,1 / 7,9 cm) e a do
  professor fecha em 1 página, terminando a 23,0 cm dos 25,7 cm úteis. Os
  rótulos de completar na grade passaram a dizer o formato (`Completar 1: …`),
  que antes apareciam só como `1)` e se confundiam com a numeração do marcar.
- Figura de apoio: teto de 17 cm de altura além dos 14 cm de largura — imagem
  retrato de 14 cm não cabe na área útil do A4 com legenda e citação e sairia
  cortada; medido em impressão real (14,00×7,88 cm, 14,00×14,00 cm e
  8,50×17,00 cm, todas centralizadas e dentro das margens).
- Log de geração registra `duracao_s` da montagem (validação + gravação), o lado
  automático da comparação da Q5.
- CI: os jobs de `ci.yml` e `projects-ci.yml` baixam as dependências e delegam a
  execução ao `scripts/test_all.sh --only <projeto>`, em vez de repetir os
  comandos; a matrix, o limite de cobertura de 70% (via `PYTEST_ADDOPTS`) e os
  artefatos continuam iguais.
- CI: `ruff` e `mypy` passam a cobrir `ai`, `api`, `src`, `scripts` e `tests`;
  `shellcheck` roda em `$(git ls-files 'scripts/*.sh')` (inclui `scripts/audio/`);
  `test-python` exige cobertura mínima de 70%.
- `mypy` com `python_version = "3.12"` — os stubs do numpy ≥ 2.5 usam `type`
  statements (PEP 695), que exigem 3.12+.
- `README.md`, `README.en.md`, `LICENSE` e `ENV_LOCAL_GEMINI.md` restaurados, e
  `Dockerfile`/`docker-compose.yml` versionados.
- Hooks de pre-commit com `mypy` e `shellcheck`; todos os `.sh` limpos.
- Dependências atualizadas e revalidadas: Python (`fastapi` 0.162, `pydantic`
  2.14, `pydantic-settings` 2.16, `openai` 3.42, `numpy` 2.5.4,
  `qdrant-client` 1.20, `uvicorn` 0.54, `pytest` 9.2, `ruff` 0.17,
  `mypy` 2.4, `python-dotenv` 1.2, `langchain-*`, `transformers` 5.22,
  `openvino` 2026.4 com `openvino-tokenizers` alinhado) e npm (`next` 16.4.3,
  `react` 19.3.1, `vite` 8.3 no dashboard de `Projetos/web`, `vite` 6.4.5 no
  dashboard da raiz). `npm audit fix` zerou as vulnerabilidades do dashboard da
  raiz e derrubou as de `Projetos/web/dashboard` de 14 para 11 (restantes só na
  cadeia dev do eslint, que exige major 10).
- Majors de frontend: `web/dashboard` sobe `vite` 6 → 8, `@vitejs/plugin-react`
  4 → 6, `lucide-react` 0.485 → 1.66 e `typescript` 5.7 → 7.0 (`tsc` nativo);
  `Projetos/next-app` sobe `eslint` 9 → 10. `recharts` foi removido do dashboard
  da raiz — estava declarado mas não era importado em nenhum arquivo de `src`,
  e a major 3 dele é incompatível. No lucide 1.x os ícones de marca saíram do
  pacote, então `Github` virou `GitBranch` em `Landing.tsx`.

### Corrigido

- Auditoria do Google Drive: a reanálise sobre o inventário já deduplicado por
  id elimina 20.443 linhas que eram "duplicata do próprio arquivo" (pasta de
  topo re-listada pelo crawl antigo) — de 41.389 para 27.543 grupos e de 67.447
  para 47.004 cópias para lixeira, incluindo as 23.389 linhas falsas da pasta
  `PDF`.
- `flask` e `python-dotenv` declarados no extra `dev` — `tests/test_coraci_app.py`
  carrega o app Flask legado.
- Assets do app Flask legado (`templates/`, `static/`) e o dashboard Vite
  restaurados; `build-dashboard` e `test-shell` agora **falham** quando o alvo
  não existe, em vez de reportar sucesso sem construir/executar nada.
- Chat: HTTP 402/429 (cobrança/cota) nunca é resolvido gastando — o fluxo cai
  para modelo gratuito (`:free`) ou provedor local, com mensagem de custo zero.
- `TaskType.refactor` de volta ao roteamento, apontando para o Ollama local.
- Fixture `app` renomeada para `fastapi_app` nos testes (colidia com o
  `pytest-flask`).
- `np.asarray` em `remove_silence` — o numpy 2.5 rejeita a união
  `float | ndarray`.
- `typescript` fica em 6.x em `Projetos/next-app` e `Projetos/web/dashboard`: o
  `typescript-eslint` 8.72 recusa TS 7 (`does not support TS 7.0`), e é ele que
  sustenta o `npm run lint` dos dois no CI. TS 7 entra só no dashboard da raiz,
  que não tem lint. Reavaliar quando sair o suporte a 7.1
  (typescript-eslint#10940).

### Segurança

- Autenticação por API key (`X-API-Key`) nos routers `/api/v2`, validação
  anti-SSRF de `api_base_url` e isolamento do estado do Coraci entre testes.
- Chave do Coraci movida de `config.json` para variável de ambiente.
- Provedor fantasma `freebuff` removido do roteamento e de `/api/providers`.
- Validação de entrada no chat do Coraci e no endpoint de configuração.

### Removido

- Instalador do Microsoft Office 2016 via Wine:
  `scripts/install_office2016_msi.sh`, `scripts/setup_office_wine.sh`,
  `scripts/diagnose_office_linux.sh`, `docs/microsoft-office-linux-wine.md` e
  `tests/shell/test_install_office2016_msi.bats`.

## [2.1.1] — 2026-08-10

### Adicionado

- Ferramentas de primeira parte versionadas em `scripts/`, portal educacional e
  documentação do Office (`3bf31a28`).

### Alterado

- CI padronizado no `ruff`: `check` usando a configuração do `pyproject.toml` e
  `format` no lugar do `black` (removidos `black` e `isort` órfãos do extra
  `dev`); suíte do `leituraia` incluída no pipeline.
- Testes de VAD dão `skip` quando o `webrtcvad` não importa (extensão C antiga
  falha no Python 3.12 do runner).

## [2.1.0] — 2026-08-10

### Adicionado

- Primeira release com tag do monolito unificado `ia-lab-unified`: FastAPI com
  chat SSE (Coraci), áudio (STT/TTS), RAG com memória vetorial (Qdrant),
  inferência OpenVINO/BitNet, módulo educacional (HistóriaIA) e dashboard Vite.

[Não publicado]: https://github.com/flavioptu2007-svg/IA-Lab-Monolito/compare/v2.1.1...HEAD
[2.1.1]: https://github.com/flavioptu2007-svg/IA-Lab-Monolito/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/flavioptu2007-svg/IA-Lab-Monolito/releases/tag/v2.1.0
