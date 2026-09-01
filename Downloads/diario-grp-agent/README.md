# Diário GRP Agent

Agente local para automatizar rotinas do GRPWeb/SGE com validação e trilha de auditoria.

## Estado desta versão

A versão 0.2.0 implementa o núcleo de domínio, inspeção do Excel, descoberta genérica com Playwright, planejamento seguro de notas, CLI e interfaces para aulas, frequência e relatórios.

A execução de escrita no GRP real continua deliberadamente protegida até a calibração dos seletores na sessão autenticada. O agente não guarda senha.

## Instalação no Linux

```bash
cd /mnt/data/diario-grp-agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
python -m playwright install chromium
```

Se o Chromium do sistema já estiver instalado, o agente também consegue usá-lo quando localizado em `/usr/bin/chromium`.

## Primeira execução

```bash
source .venv/bin/activate
python -m grp_agent.cli discover
```

O navegador abre visível. Faça o login no GRP manualmente, se solicitado. A sessão fica no diretório local `state/playwright/`; a senha não é registrada pelo agente.

## Calibrar o GRP real

Depois de fazer login, use a calibração para capturar o DOM da tela autenticada que será automatizada:

```bash
python -m grp_agent.cli calibrate
```

1. Faça o login manualmente.
2. Navegue até a tela desejada (por exemplo, Pesquisa de Resultados de Avaliações).
3. Volte ao terminal e pressione Enter.
4. O agente salva `page.html`, `visible.txt`, `url.txt`, `title.txt` e uma captura PNG em `artifacts/calibration/`.

Esses artefatos permitem calibrar os seletores reais sem guardar senha ou cookies fora do perfil local.

## Simular lançamento (fluxo padrão): audit-preview

```bash
python -m grp_agent.cli audit-preview \
  --file '/caminho/Notas AGT e Ciclo 2 - Trimestre 2.xlsx'
```

Análise 100% offline e somente leitura: detecta turma, alunos, fontes de nota,
regra de cálculo (deduzida das fórmulas, nunca por posição de coluna) e escalas.
Este comando **não possui caminho de escrita no GRP** — nem com flags.
Sem regra suficiente ou com ambiguidade não resolvida, o aluno/aba é BLOQUEADO.

Opções: `--sheet` (uma aba), `--target-max N` (escala de destino; sem ela
nenhuma conversão é feita), `--final-column` (modo manual explícito) e
`--compare-grp` (comparação somente leitura com o GRP, interativa).

## Modo legado/manual: grades

```bash
python -m grp_agent.cli grades \
  --file '/mnt/data/Notas AGT e Ciclo 2 - Trimestre 2.xlsx' \
  --period '2º TRIMESTRE' \
  --evaluation 'AVALIAÇÃO BIMESTRAL' \
  --column L
```

AVISO: o parâmetro `--column` (padrão `L`) **não é regra de negócio** — é um
modo legado para inspeção manual por coluna fixa. A nota pode estar em qualquer
coluna; use `audit-preview` como fluxo padrão. `DRY-RUN` por padrão; nada é
salvo no GRP.

## Operações previstas

```text
grp-agent discover
grp-agent audit
grp-agent grades --file ARQUIVO.xlsx --period '2º TRIMESTRE'
grp-agent lessons
grp-agent attendance
grp-agent reports
```

Para operações de escrita, o fluxo previsto é: descoberta → auditoria → plano → confirmação explícita → execução → validação pós-salvamento → registro de auditoria.

## Segurança

- Nunca coloque usuário ou senha em `.env`, código ou argumentos do comando.
- Não compartilhe o diretório `state/playwright/`.
- Faça uma cópia/backup dos dados antes de executar operações de escrita em produção.
- Use `DRY-RUN` para revisar correspondências antes de usar `--apply`.

## Limitação atual

Os elementos visuais do GRP apresentados nas capturas são suficientes para modelar o fluxo, mas os seletores exatos das telas autenticadas ainda precisam ser calibrados no navegador real. Isso deve ser feito antes da primeira operação que clique em `Salvar`.

## Atalho sem instalação editável

Depois de instalar as dependências, o projeto também pode ser executado sem `pip install -e`:

```bash
./grp-agent.sh calibrate
./grp-agent.sh discover
./grp-agent.sh grades --file '/caminho/arquivo.xlsx' --period '2º TRIMESTRE' --column L
```

Para instalar o Chromium usado pelo Playwright, se necessário:

```bash
python3 -m playwright install chromium
```


## Inspeção da captura
Após executar `calibrate`, use `./grp-agent.sh inspect-dom` para inventariar IDs,
names, classes, roles, placeholders e botões do último `page.html`. O HTML é
analisado localmente; o agente não envia a captura para a internet.

---

## DeepSeek-R1 Evaluation Suite

Avaliação abrangente de modelos de raciocínio (DeepSeek-R1, Llama 4, Qwen3, Gemini) usando [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness).

### Quick Start

```bash
# 1. Instalar dependências
pip install lm-eval[openai] openrouter

# 2. Configurar chave API
export OPENROUTER_API_KEY="sua_chave_aqui"

# 3. Rodar comparação rápida (modelos gratuitos)
./run_quick_compare.sh --free-only --limit 5

# 4. Rodar comparação completa (15 modelos)
./run_quick_compare.sh --limit 10
```

### Scripts

| Script | Uso | Custo |
|--------|-----|-------|
| `run_quick_compare.sh` | Comparação rápida multi-modelo via OpenRouter | Variável |
| `run_deepseek_eval.sh` | Suite completa (vLLM local + API, 74 execuções) | Variável |
| `parse_sc_results.py` | Agregação de auto-consistência (majority vote) | Grátis |

### Benchmarks

| Benchmark | Tarefa | Tipo |
|-----------|--------|------|
| GSM8K CoT | Matemática fundamental com passos | Geração |
| Hendrycks Math | Matemática avançada (olimpíada) | Geração |
| GPQA Diamond CoT | Ciências nível pós-graduação | Geração |
| AIME 2024 | Competição matemática | Geração |
| MMLU | Conhecimento geral | Múltipla escolha |

### Modelos Suportados

| Modelo | Provider | Custo (Input/Output por 1M tokens) |
|--------|----------|-------------------------------------|
| DeepSeek-R1 (671B) | DeepSeek API / OpenRouter | $0.55-$0.70 / $2.19-$2.50 |
| DeepSeek-V4-Flash | DeepSeek API | $0.22 / $0.66 |
| Llama 4 Maverick | OpenRouter | $0.20 / $0.70 |
| Llama 4 Scout | OpenRouter | $0.10 / $0.30 |
| Qwen3-32B | OpenRouter | $0.08 / $0.28 |
| Gemini 2.5 Flash | OpenRouter | $0.30 / $2.50 |
| Nemotron-3 Ultra 550B | OpenRouter | **Grátis** |
| Gemma 4 31B | OpenRouter | **Grátis** |

### Configurar OpenRouter

```bash
# Obter chave em: https://openrouter.ai/keys
export OPENROUTER_API_KEY="sk-or-v1-..."

# Usar com lm-eval
export OPENAI_API_KEY="$OPENROUTER_API_KEY"
lm_eval --model local-chat-completions \
  --model_args model=deepseek/deepseek-r1,base_url=https://openrouter.ai/api/v1 \
  --tasks gsm8k_cot \
  --limit 10

# Ou usar o script rápido
API_PROVIDER=openrouter ./run_quick_compare.sh
```

### CI/CD

O workflow GitHub Actions (`.github/workflows/deepseek-eval.yml`) roda automaticamente:
- **Semanalmente** (domingos 06:00 UTC — off-peak para DeepSeek API)
- **Manualmente** via `workflow_dispatch`
- **Ao alterar** scripts de avaliação no `main`

Requer o secret `OPENROUTER_API_KEY` no repositório.

### Custos Estimados

| Cenário | Custo estimado |
|---------|----------------|
| Modelos gratuitos (Nemotron, Gemma) | $0 |
| Qwen3-32B (10 perguntas/task) | ~$0.01 |
| DeepSeek-R1 completo (1320 perguntas) | ~$6 |
| Suite completa (5 benchmarks × 1320) | ~$32 |

Veja `COST_COMPARISON.md` para análise detalhada.

### Auto-consistência (Self-Consistency)

```bash
# Rodar 8 amostras por pergunta e agregar por majority vote
./run_deepseek_eval.sh  # inclui PART 3

# Ou agregar resultados existentes
python3 parse_sc_results.py --results_dir ./deepseek_eval_results --num_samples 8
```
