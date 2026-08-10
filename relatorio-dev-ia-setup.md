# Relatório de Instalação e Configuração — Ambiente Dev IA

**Data:** 10 de julho de 2026
**Usuário:** flavio
**Sistema:** Ubuntu 26.04 LTS (resolute) — x86_64

---

## Resumo Executivo

| Componente | Status | Observação |
|---|---|---|
| Sistema Operacional | ✅ OK | Ubuntu 26.04 LTS, 16 cores, 30 GB RAM |
| Python + Pacotes IA | ✅ OK | Python 3.14.4, stack completa instalada |
| Cursor Desktop | ✅ OK | v3.10.20, CLI funcional |
| Cursor Settings | ✅ OK | settings.json criado e otimizado |
| Extensões Cursor | ⚠️ Atenção | 24 extensões; GitHub Copilot indisponível no Cursor |
| Ollama | ✅ OK | v0.30.10, 13 modelos, inferência testada |
| OpenVINO | ✅ OK | v2026.2.1, CPU + GPU Intel detectados |
| Docker | ✅ OK | v29.1.3, Compose v2.29.0, grupo docker ativo |
| Git | ✅ OK | Configurado com gh credential + Cursor editor |
| MCP | ⚠️ Atenção | 4 servidores configurados; 4 indisponíveis no npm |
| OpenAI API | ❌ Falha | OPENAI_API_KEY não configurada — **intervenção manual** |
| Pacotes apt | ⚠️ Atenção | bat, clang, java, imagemagick, postgresql-client pendentes — **intervenção manual (sudo)** |
| Atualização sistema | ⚠️ Atenção | 44 pacotes pendentes — **intervenção manual (sudo)** |
| Memória/Swap | ⚠️ Atenção | Swap 100% utilizado (8 GB) — risco de performance |
| GPU NVIDIA | ⚠️ Atenção | Não detectada; Intel UHD Graphics ativa via i915 |
| NPU Intel | ⚠️ Atenção | Dispositivo /dev/accel não detectado |

---

## 1. Sistema

| Item | Valor |
|---|---|
| SO | Ubuntu 26.04 LTS (resolute) |
| Arquitetura | x86_64 |
| CPU | Intel Core i7-13620H (13th Gen) — 10 cores / 16 threads @ 4.9 GHz |
| RAM | 30 GB total (8.1 GB disponível no momento do diagnóstico) |
| Swap | 8 GB (**100% utilizado** — atenção crítica) |
| Disco | NVMe 915 GB — 364 GB usados, 505 GB livres (42%) |
| GPU | Intel Raptor Lake-P UHD Graphics (i915 driver ativo) |
| GPU NVIDIA | Não presente / driver não instalado |

---

## 2. Versões Instaladas

| Software | Versão | Status |
|---|---|---|
| Python | 3.14.4 | ✅ |
| pip | 25.1.1 | ✅ |
| Git | 2.53.0 | ✅ |
| Node.js | v24.18.0 | ✅ |
| npm | 11.16.0 | ✅ |
| Docker | 29.1.3 | ✅ |
| Docker Compose | v2.29.0 | ✅ |
| Ollama | 0.30.10 | ✅ |
| Cursor | 3.10.20 | ✅ |
| OpenVINO | 2026.2.1 | ✅ |
| GCC | 15.2.0 | ✅ |
| CMake | 4.3.4 | ✅ |
| jq | 1.8.1 | ✅ |
| gh (GitHub CLI) | instalado | ✅ |
| Java | — | ❌ Não instalado |
| Clang | — | ❌ Não instalado |
| bat | — | ❌ Não instalado (batcat disponível após apt) |
| delta (git diff) | — | ❌ Não instalado |

---

## 3. Softwares Instalados / Configurados

### Já presentes (pré-configuração)
- Git, Python 3.14, pip, curl, wget, Node, npm, Docker, Ollama, OpenVINO, GCC, CMake, build-essential
- tree, htop, ripgrep, fd-find, fzf, unzip, zip, ffmpeg, sqlite3, python3-venv

### Instalados nesta sessão (pip --user)
- jupyter, ipykernel, notebook, jupyterlab
- chromadb, qdrant-client
- opencv-python, torchvision
- fastapi (atualizado)

### Pendentes (requer sudo)
Execute: `bash ~/install-system-packages.sh`

Pacotes: bat, clang, imagemagick, p7zip-full, postgresql-client, redis-tools, openjdk-21-jdk, git-delta, linux-firmware

---

## 4. Extensões Cursor Instaladas (24)

| Extensão | ID | Status |
|---|---|---|
| Python | ms-python.python | ✅ |
| Pylance/Pyright | anysphere.cursorpyright | ✅ |
| Jupyter | ms-toolsai.jupyter | ✅ |
| Docker | ms-azuretools.vscode-docker | ✅ |
| GitLens | eamodio.gitlens | ✅ |
| Ruff | charliermarsh.ruff | ✅ |
| Black Formatter | ms-python.black-formatter | ✅ |
| Error Lens | usernamehw.errorlens | ✅ |
| YAML | redhat.vscode-yaml | ✅ |
| Markdown | yzhang.markdown-all-in-one | ✅ |
| REST Client | humao.rest-client | ✅ |
| GitHub Pull Requests | github.vscode-pull-request-github | ✅ |
| Remote SSH | anysphere.remote-ssh | ✅ |
| Continue | continue.continue | ✅ |
| Code Spell Checker | streetsidesoftware.code-spell-checker | ✅ |
| Better Comments | aaron-bond.better-comments | ✅ |
| Todo Tree | gruntfuggly.todo-tree | ✅ |
| Prettier | esbenp.prettier-vscode | ✅ |
| Remote Containers | anysphere.remote-containers | ✅ |
| GitHub Copilot | GitHub.copilot | ❌ Indisponível (Cursor usa IA própria) |

---

## 5. Modelos Ollama

| Modelo | Tamanho | Status |
|---|---|---|
| qwen3:14b | 9.3 GB | ✅ Já existia |
| qwen3:8b | 5.2 GB | ✅ Já existia |
| mistral / mistral:7b-instruct | 4.4 GB | ✅ Já existia |
| mistral-small | 14 GB | ✅ Já existia |
| deepseek-r1:7b | 4.7 GB | ✅ Já existia |
| llama3.2 | 2.0 GB | ✅ Já existia (inferência testada) |
| nomic-embed-text | 274 MB | ✅ Já existia |
| hermes3, nemotron-mini, glm4, command-r, llava | diversos | ✅ Extras |

**Total:** 13 modelos (~65 GB em `~/.ollama`)

---

## 6. Configuração Git

**Arquivo:** `~/.gitconfig` (backup em `~/backups/dev-setup-20260710/`)

| Configuração | Valor |
|---|---|
| Nome | Flávio Alexandre dos Santos |
| Email | flavioptu2007@gmail.com |
| Editor | cursor --wait |
| Branch padrão | main |
| Credential helper | manager + gh auth git-credential |
| Autofetch | via Cursor settings (git.autofetch: true) |
| Diff aprimorado | algorithm=histogram, colorMoved=zebra |
| Merge aprimorado | conflictstyle=diff3, rerere enabled |
| Pager | less -R (delta pendente de instalação apt) |

---

## 7. Configuração Docker

| Item | Status |
|---|---|
| Daemon | ✅ Ativo |
| Grupo docker | ✅ flavio membro |
| Containers ativos | 5 (ia-backend, ia-grafana, ia-prometheus, +2) |
| Imagens | 40 |
| Compose | ✅ v2.29.0 via plugin |
| GPU NVIDIA | ❌ Não aplicável |
| GPU Intel (OpenVINO) | ✅ CPU + GPU via OpenVINO |
| Integração Ollama | Ollama roda nativo (systemd), não em container |

---

## 8. Configuração Cursor

**Settings:** `~/.config/Cursor/User/settings.json`

Configurado para:
- Python com Ruff (format + lint on save)
- Auto Save (1s delay)
- Tema Dark Modern, font JetBrains Mono
- Minimap habilitado, inline suggestions ativas
- Terminal bash, scrollback 10k
- Git autofetch, smart commit
- Performance: watcher excludes para node_modules, venv, cache
- Jupyter otimizado

---

## 9. Configuração Python

**Pacotes principais instalados:**

```
black, ruff, pytest, numpy, pandas, matplotlib, jupyter, ipykernel,
openai, ollama, fastapi, uvicorn, rich, typer, langchain, langgraph,
chromadb, qdrant-client, sentence-transformers, transformers,
torch (2.13.0+cpu), torchvision, torchaudio, opencv-python,
pillow, requests, httpx
```

**Tamanho:** ~3.3 GB em `~/.local/lib/python3.14/`

---

## 10. Configuração OpenVINO

| Item | Status |
|---|---|
| Toolkit Python | ✅ 2026.2.1 |
| Runtime | ✅ Funcional |
| Dispositivos | CPU, GPU |
| NPU | ❌ Não detectado |
| Model Zoo | Via pip (openvino-tokenizers instalado) |
| Teste | ✅ `Core().available_devices = ['CPU', 'GPU']` |

---

## 11. Configuração MCP

**Arquivo:** `~/.cursor/mcp.json`

| Servidor | Status | Notas |
|---|---|---|
| Filesystem | ✅ Configurado | `@modelcontextprotocol/server-filesystem` |
| GitHub | ✅ Configurado | Requer `GITHUB_PERSONAL_ACCESS_TOKEN` |
| Postgres | ✅ Configurado | Requer PostgreSQL local na porta 5432 |
| Brave Search | ✅ Configurado | Requer `BRAVE_API_KEY` |
| Git | ❌ Indisponível | Pacote npm não existe |
| Docker | ❌ Indisponível | Pacote npm não existe |
| SQLite | ❌ Indisponível | Pacote npm não existe |
| Fetch | ❌ Indisponível | Pacote npm não existe |

**Servidores nativos do Cursor (já ativos):**
- cursor-app-control
- cursor-ide-browser

---

## 12. Variáveis de Ambiente

**Arquivo:** `~/.config/dev-env.sh` (sourced via `~/.profile`)

| Variável | Valor |
|---|---|
| PATH | `$HOME/.local/bin:$HOME/bin:$PATH` |
| PYTHONPATH | `~/.local/lib/python3.14/site-packages` |
| OLLAMA_HOST | `http://127.0.0.1:11434` |
| OLLAMA_MODELS | `~/.ollama/models` |
| OPENAI_API_KEY | ❌ **Não configurada** |
| CUDA_VISIBLE_DEVICES | "" (sem NVIDIA) |
| JAVA_HOME | Comentado (Java não instalado) |
| DOCKER_BUILDKIT | 1 |
| EDITOR/VISUAL/GIT_EDITOR | cursor --wait |

---

## 13. Aliases Criados

**Arquivo:** `~/.bash_aliases`

| Alias | Função |
|---|---|
| `ll` | ls -alFh colorido |
| `update` | apt upgrade + snap + flatpak |
| `docker-clean` | prune completo Docker |
| `python-server` | HTTP server porta 8080 |
| `git-clean` | limpa branches merged |
| `cursor-update` | verifica versão Cursor |
| `ollama-update` | reinstala/atualiza Ollama |
| `dps`, `dlogs`, `dexec` | atalhos Docker |
| `py`, `pip`, `venv` | atalhos Python |

---

## 14. Espaço Utilizado

| Local | Tamanho |
|---|---|
| Disco total usado | 364 GB / 915 GB |
| Disco livre | 505 GB |
| Modelos Ollama | ~65 GB |
| Python packages | ~3.3 GB |
| pip cache (após limpeza) | ~1.8 GB |

---

## 15. Problemas Encontrados

1. **Swap 100% utilizado** — 8 GB de swap completamente cheio, apenas 995 MB RAM livre
2. **Sudo requer senha interativa** — impossível executar apt upgrade/install automaticamente
3. **OPENAI_API_KEY ausente** — variável de ambiente não definida
4. **GitHub Copilot** — extensão não instalável no Cursor (usa IA nativa)
5. **4 servidores MCP indisponíveis** no registro npm (git, docker, sqlite, fetch)
6. **Pacotes apt faltando:** bat, clang, java, imagemagick, postgresql-client, p7zip-full, redis-tools, git-delta
7. **44 pacotes apt desatualizados**
8. **NPU Intel não detectada** — apenas CPU e GPU OpenVINO disponíveis
9. **Sem GPU NVIDIA** — torch instalado como CPU-only

---

## 16. Problemas Corrigidos

1. ✅ Criado `settings.json` otimizado para Cursor (não existia)
2. ✅ Instalados 18 pacotes Python faltantes (jupyter, chromadb, qdrant, opencv, torchvision)
3. ✅ Instaladas 22 extensões Cursor
4. ✅ Configurado Git completo (editor Cursor, branch main, gh credential, diff/merge)
5. ✅ Criado MCP config com servidores disponíveis
6. ✅ Criados aliases úteis em `~/.bash_aliases`
7. ✅ Criado `~/.config/dev-env.sh` com variáveis de ambiente
8. ✅ Backups criados em `~/backups/dev-setup-20260710/`
9. ✅ Cache pip limpo (168 MB removidos)
10. ✅ Corrigido JSON inválido no mcp.json
11. ✅ Criado script `~/install-system-packages.sh` para pacotes sudo

---

## 17. Intervenção Manual Necessária

### Prioridade Alta

```bash
# 1. Instalar pacotes do sistema (requer senha sudo)
bash ~/install-system-packages.sh

# 2. Configurar OpenAI API Key
echo 'export OPENAI_API_KEY="sk-sua-chave-aqui"' >> ~/.config/dev-env.sh
source ~/.config/dev-env.sh

# 3. Liberar swap (swap 100% cheio)
sudo swapoff -a && sudo swapon -a
# Considere aumentar RAM swap ou fechar processos pesados
```

### Prioridade Média

```bash
# 4. Configurar tokens MCP
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."' >> ~/.config/dev-env.sh
echo 'export BRAVE_API_KEY="BSA..."' >> ~/.config/dev-env.sh

# 5. Recarregar ambiente
source ~/.profile
```

### Prioridade Baixa

- Instalar GitHub Copilot não é necessário (Cursor tem IA integrada)
- NPU Intel: verificar se o hardware suporta e instalar driver `intel-npu-driver`
- Considerar GPU NVIDIA dedicada se workloads de deep learning forem intensivos

---

## 18. Sugestões de Melhoria

1. **Memória:** Swap completamente cheio indica pressão de memória. Feche containers/apps não usados ou considere upgrade de RAM.
2. **Ollama:** 65 GB de modelos — considere remover modelos não usados (`ollama rm <modelo>`).
3. **PyTorch GPU:** Para Intel GPU, considere `pip install intel-extension-for-pytorch` para acelerar inferência.
4. **Docker + Ollama:** Para isolamento, rode Ollama em container com GPU passthrough.
5. **Monitoramento:** Containers ia-grafana e ia-prometheus já estão ativos — configure dashboards.
6. **CI/CD:** gh CLI já instalado — configure `gh auth login` se ainda não feito.
7. **Backup regular:** Automatize backup de `~/.cursor`, `~/.config/Cursor`, `~/.gitconfig`.
8. **Python venv:** Para projetos, use sempre venv (`alias venv` já configurado).

---

## 19. Testes Realizados

| Teste | Resultado |
|---|---|
| Python imports (numpy, torch, openvino, langchain, chromadb, cv2) | ✅ PASS |
| Docker ps + compose version | ✅ PASS |
| Git config + version | ✅ PASS |
| Cursor --version | ✅ PASS |
| Ollama list + inference (llama3.2) | ✅ PASS |
| OpenVINO devices (CPU, GPU) | ✅ PASS |
| Node + npm version | ✅ PASS |
| Jupyter version | ✅ PASS |
| MCP packages npm availability | ⚠️ 4/8 disponíveis |

---

## 20. Arquivos Criados/Modificados

| Arquivo | Ação |
|---|---|
| `~/.config/Cursor/User/settings.json` | Criado |
| `~/.cursor/mcp.json` | Criado |
| `~/.gitconfig` | Atualizado |
| `~/.bash_aliases` | Criado |
| `~/.config/dev-env.sh` | Criado |
| `~/.profile` | Atualizado (source dev-env.sh) |
| `~/install-system-packages.sh` | Criado |
| `~/data/dev.db` | Criado (placeholder SQLite) |
| `~/backups/dev-setup-20260710/` | Backups |

---

*Relatório gerado automaticamente em 10/07/2026.*
