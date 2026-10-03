# Design: Auditoria e Renomeação Arquivística do Google Drive

**Data:** 2026-10-02
**Status:** Aprovado em brainstorming — aguardando review do usuário
**Escopo:** Google Drive inteiro (`rclone` remote `gdrive:`)

## 1. Objetivo

Auditar o Google Drive completo para:

1. Inventariar pastas e arquivos (metadados).
2. Identificar pastas vazias (candidatas a exclusão).
3. Propor renomeação de arquivos e pastas no padrão arquivístico `AAAA-MM-DD_Tipo_Assunto_Versao`.
4. **Não alterar nada no Drive** até aprovação explícita por lote.

### Entregáveis

Todos em `~/drive-audit/`:

| Arquivo | Conteúdo |
|---------|----------|
| `inventory.csv` | Inventário: path, name, id, size, mime, modified, created, is_dir |
| `empty_folders.csv` | Pastas vazias (recursivo) com path e id |
| `rename_plan.csv` | `path_atual`, `nome_atual`, `nome_sugerido`, `motivo`, `confianca` |
| `summary.md` | Resumo executivo, contagens, riscos, lacunas de cota |
| `logs/` | Logs de inventário e (futuro) apply |

## 2. Arquitetura

```
gdrive: (rclone)
    │
    ▼
[1] Inventário com throttle  →  inventory.jsonl / inventory.csv
    │
    ▼
[2] Detector de pastas vazias →  empty_folders.csv
    │
    ▼
[3] Classificador de nomes    →  rename_plan.csv
    │
    ▼
[4] Relatório summary.md      →  revisão humana
    │
    ▼
[5] Apply por lote (pós-aprovação): dry-run → apply + log
```

### Componentes

- **rclone** (`gdrive:`): listagem e, após aprovação, `rmdir` / `moveto` / `backend` rename.
- **Scripts Python** em `~/drive-audit/scripts/`:
  - `inventory.py` — orquestra listagem (rclone ou API) com retry/backoff.
  - `find_empty.py` — calcula pastas vazias a partir do inventário.
  - `suggest_names.py` — aplica regras de nomenclatura.
  - `apply_batch.py` — dry-run/apply de um lote aprovado (CSV filtrado).
- **Sem leitura de conteúdo** de PDF/DOCX/Docs nesta versão (só metadados + nome + caminho).

### Pasta de trabalho

`~/drive-audit/` — artefatos locais apenas; não sincroniza de volta ao Drive.

## 3. Regras de nomenclatura

### Formato

```
AAAA-MM-DD_Tipo_Assunto_Versao.ext
```

Exemplos:

- `2026-03-15_Atividade_AstecasMaiasIncas_v01.pdf`
- `2025-08-16_Apostila_CacaPalavrasDidaticos_v01.zip`
- `2026-04-20_Plano_Abril2026_v01` (pasta)

### Campos

| Campo | Regra |
|-------|--------|
| **Data** | 1) extrair de padrão no nome atual (`YYYYMMDD`, `YYYY-MM-DD`, `YYYY`); 2) senão `modifiedTime` do Drive; 3) senão `createdTime`. |
| **Tipo** | Vocabulário fechado: `Atividade`, `Plano`, `Avaliacao`, `Apostila`, `Slides`, `Artigo`, `Backup`, `Registro`, `Material`, `Outro`. Inferido por palavras-chave no path/nome. |
| **Assunto** | TitleCase ASCII sem acentos; remove ruído (`Cópia de`, `(1)`, timestamps de zip do Drive); máx. ~60 caracteres. |
| **Versao** | `v01` default; incrementa se detectar `(1)`, `(2)`, `Cópia`, `copy`, ou colisão no mesmo diretório. |
| **ext** | Extensão original em minúsculas; Google Docs nativos ficam sem extensão de arquivo “falso” (mantém tipo MIME / nome lógico). |

### Normalização de caracteres

- Sem espaços (underscores só entre campos principais).
- Sem acentos (NFKD → ASCII).
- Proibidos: `# [ ] { } \ | < > ? * : " /`
- Pastas seguem o mesmo espírito (data_tipo_assunto quando aplicável; pastas “container” de série/ano podem usar forma curta normalizada, ex. `06_Ano`).

### O que NÃO renomear automaticamente no plano

- Arquivos cujo nome **já** está no padrão (marcar `ok` / skip).
- Itens em que a confiança da sugestão for baixa (`confianca=baixa`) — listar para decisão manual.

## 4. Pastas vazias e segurança

### Definição de pasta vazia

Pasta sem arquivos e sem subpastas com conteúdo (vazio transitivo). Calculado offline a partir do inventário completo.

### Política

- Atalhos dangling: **relatório apenas**, não apagar sozinhos.
- Nunca apagar automaticamente: pastas com conteúdo, itens “Shared with me” sem confirmação, Lixeira.
- Exclusão e renomeação: **sempre** dry-run → aprovação do usuário → apply em lote com log (`timestamp`, `id`, `path_antes`, `acao`, `path_depois` ou erro).
- Cota API (`RATE_LIMIT_EXCEEDED`): backoff exponencial, pausa, retoma; lacunas documentadas em `summary.md`.

### Lotes sugeridos na fase apply

1. Pastas vazias (só exclusão).
2. Renomeações de alta confiança.
3. Renomeações de confiança média (revisão linha a linha se o usuário pedir).

## 5. Critérios de sucesso

- Inventário do Drive (ou inventário parcial com lacunas de cota explícitas).
- Lista revisável de pastas vazias.
- Plano de renomeação revisável no padrão acordado.
- **Zero alteração** no Drive até autorização explícita de cada lote.
- Após apply autorizado: log reproduzível e contagem de sucessos/falhas.

## 6. Fora de escopo (esta versão)

- Leitura de conteúdo (OCR / texto de PDF/DOCX).
- Deduplicação por hash / fusão de duplicatas de conteúdo.
- OneDrive / Dropbox.
- Reorganização profunda de árvore (mover entre pastas), além de renomear no lugar e apagar vazias.

## 7. Riscos

| Risco | Mitigação |
|-------|-----------|
| Cota Google Drive API | Throttle, retry, inventário incremental |
| Renomear link compartilhado | Preferir rename in-place (mesmo file id); avisar no summary |
| Colisão de nomes | Sufixo `_vNN` ou `_dupN` no plano |
| Home git “sujo” | Artefatos em `~/drive-audit/`; não misturar com outros projetos |

## 8. Próximo passo

Após aprovação desta spec: skill **writing-plans** → plano de implementação passo a passo, depois execução (inventário primeiro).
