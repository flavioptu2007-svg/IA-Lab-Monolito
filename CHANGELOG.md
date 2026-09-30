# Changelog

Todas as mudanças relevantes deste projeto são registradas neste arquivo.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
versionamento segue o [SemVer](https://semver.org/lang/pt-BR/). A versão corrente
é a declarada em `pyproject.toml` (`2.1.1`).

## [Não publicado]

### Adicionado

- `Projetos/next-app`, `Projetos/web` e `Projetos/leituraia` versionados: os
  caminhos exigidos pelo `projects-ci.yml` existiam apenas no disco, e os 4 jobs
  falhavam com "working directory not found".
- `tests/shell/test_scripts_smoke.bats`: 5 testes bats cobrindo os 15 scripts
  shell versionados (existência, `bash -n`, shebang, `--help` e convenção de
  nomes de arquivo).
- `tests/test_core_config.py`: testes de `src/core/config.py` — defaults,
  override por variável de ambiente e a guarda que impede subir em produção com
  o segredo JWT padrão.
- `.dockerignore` em allowlist, para o contexto de build da imagem não incluir
  segredos nem o repositório inteiro.
- Documentação comunitária: `SECURITY.md` (divulgação responsável) e
  `.github/dependabot.yml` (atualizações semanais de `pip`, `npm`, `docker` e
  GitHub Actions).

### Alterado

- CI: `ruff` e `mypy` passam a cobrir `ai`, `api`, `src`, `scripts` e `tests`;
  `shellcheck` roda em `$(git ls-files 'scripts/*.sh')` (inclui `scripts/audio/`);
  `test-python` exige cobertura mínima de 70%.
- `mypy` com `python_version = "3.12"` — os stubs do numpy ≥ 2.5 usam `type`
  statements (PEP 695), que exigem 3.12+.
- `README.md`, `README.en.md`, `LICENSE` e `ENV_LOCAL_GEMINI.md` restaurados, e
  `Dockerfile`/`docker-compose.yml` versionados.
- Hooks de pre-commit com `mypy` e `shellcheck`; todos os `.sh` limpos.

### Corrigido

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
