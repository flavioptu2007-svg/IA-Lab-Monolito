# Design: Auditoria, Deduplicação e Renomeação Arquivística do Google Drive

**Data:** 2026-10-02
**Status:** Revisado — inclui mesclagem de duplicatas; aguardando review do usuário
**Escopo:** Google Drive inteiro (`rclone` remote `gdrive:`)

## 1. Objetivo

Auditar o Google Drive completo para:

1. Inventariar pastas e arquivos (metadados + hash de conteúdo quando aplicável).
2. Identificar pastas vazias (candidatas a exclusão).
3. Detectar arquivos duplicados pelo **mesmo conteúdo (hash)** e propor mesclagem: **manter 1 cópia, enviar as outras para a lixeira**.
4. Propor renomeação de arquivos e pastas no padrão arquivístico `AAAA-MM-DD_Tipo_Assunto_Versao`.
5. **Não alterar nada no Drive** até aprovação explícita por lote.

### Entregáveis

Todos em `~/drive-audit/`:

| Arquivo | Conteúdo |
|---------|----------|
| `inventory.csv` | Inventário: path, name, id, size, mime, modified, created, is_dir, hash |
| `empty_folders.csv` | Pastas vazias (recursivo) com path e id |
| `duplicates.csv` | Grupos de duplicatas: `group_id`, `hash`, `action` (`keep`/`trash`), path, id, motivo da escolha |
| `rename_plan.csv` | `path_atual`, `nome_atual`, `nome_sugerido`, `motivo`, `confianca` |
| `summary.md` | Resumo executivo, contagens, espaço recuperável, riscos, lacunas de cota |
| `logs/` | Logs de inventário e (futuro) apply |

## 2. Arquitetura

```
gdrive: (rclone)
    │
    ▼
[1] Inventário com throttle     →  inventory.jsonl / inventory.csv
    │
    ▼
[2] Hashes (arquivos binários)  →  hash no inventário (lotes + cache)
    │
    ▼
[3] Detector de pastas vazias   →  empty_folders.csv
    │
    ▼
[4] Deduplicação por hash       →  duplicates.csv (keep / trash)
    │
    ▼
[5] Classificador de nomes      →  rename_plan.csv
    │     (só sobre cópias keep + arquivos únicos)
    ▼
[6] Relatório summary.md        →  revisão humana
    │
    ▼
[7] Apply por lote (pós-aprovação): dry-run → apply + log
```

### Componentes

- **rclone** (`gdrive:`): listagem, hash (`rclone hashsum` / metadados MD5 quando o Drive fornecer), e após aprovação: rename, `delete` para lixeira, `rmdir`.
- **Scripts Python** em `~/drive-audit/scripts/`:
  - `inventory.py` — listagem com retry/backoff.
  - `hash_files.py` — calcula/coleta hashes em lotes; cache local para não recalcular.
  - `find_empty.py` — pastas vazias a partir do inventário.
  - `find_duplicates.py` — agrupa por hash; escolhe `keep` vs `trash`.
  - `suggest_names.py` — regras de nomenclatura (após dedupe).
  - `apply_batch.py` — dry-run/apply de lote aprovado.
- **Sem leitura semântica** de PDF/DOCX (não funde texto). Hash = bytes iguais.
- Google Docs/Sheets nativos: hash de binário pode não aplicar; tratar à parte (export ou agrupar só por id/revisão) e marcar no relatório se não forem hasháveis.

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
- Cópias marcadas `trash` no plano de duplicatas (não renomear o que vai para a lixeira).

## 4. Duplicatas (mesclagem)

### Definição

Dois ou mais **arquivos** com o **mesmo hash de conteúdo** (MD5 ou SHA-1 conforme disponível no Drive/rclone) e tamanho > 0 formam um grupo.

### Escolha da cópia a manter (`keep`)

Ordem de prioridade:

1. Path **fora** de pastas cujo nome começa com / contém `Backup`, `Backups`, `BackupLinux`, `BackupDocumentos`, `AvastCleanup`, dumps óbvios.
2. Nome **mais limpo** (já no padrão arquivístico, ou sem `Cópia de` / `(1)` / timestamps de export).
3. Path **mais curto** e mais organizado (menos níveis, menos caracteres de ruído).
4. `modifiedTime` **mais recente** como desempate.

As demais entradas do grupo: `action=trash` (enviar para a **lixeira** do Drive, não exclusão permanente).

### Política

- Só arquivos hasháveis entram no lote automático de trash.
- Google Docs nativos sem hash confiável: listar em seção “revisar manualmente”, sem trash automático.
- Atalhos: não usar como `keep` preferencial; se o alvo já está no grupo, preferir o arquivo real.
- `duplicates.csv` traz sugestão `keep`/`trash` editável antes do apply.
- Apply de trash: dry-run → aprovação → lixeira + log; reversível pela lixeira do Drive por 30 dias (comportamento padrão Google).

## 5. Pastas vazias e segurança

### Definição de pasta vazia

Pasta sem arquivos e sem subpastas com conteúdo (vazio transitivo). Recalcular **depois** do lote de trash de duplicatas (pastas podem esvaziar).

### Política

- Atalhos dangling: **relatório apenas**, não apagar sozinhos.
- Nunca apagar automaticamente: pastas com conteúdo, itens “Shared with me” sem confirmação, Lixeira.
- Exclusão (vazias), trash (duplicatas) e renomeação: **sempre** dry-run → aprovação → apply com log (`timestamp`, `id`, `path_antes`, `acao`, `path_depois` ou erro).
- Cota API (`RATE_LIMIT_EXCEEDED`): backoff exponencial, pausa, retoma; lacunas documentadas em `summary.md`.

### Lotes sugeridos na fase apply

1. Duplicatas → lixeira (`trash` do CSV).
2. Pastas vazias (recalcular após o passo 1).
3. Renomeações de alta confiança (só itens `keep` / únicos).
4. Renomeações de confiança média (revisão se o usuário pedir).

## 6. Critérios de sucesso

- Inventário do Drive (ou parcial com lacunas de cota explícitas).
- Grupos de duplicatas por hash com `keep`/`trash` revisáveis e estimativa de espaço liberável.
- Lista revisável de pastas vazias.
- Plano de renomeação revisável no padrão acordado.
- **Zero alteração** no Drive até autorização explícita de cada lote.
- Após apply autorizado: log reproduzível e contagem de sucessos/falhas.

## 7. Fora de escopo (esta versão)

- Fusão de **texto** entre documentos diferentes (merge semântico de PDF/DOCX).
- Deduplicação só por nome similar sem hash (exceto relatório auxiliar opcional).
- OneDrive / Dropbox.
- Reorganização profunda de árvore (mover entre pastas), além de renomear no lugar, trash de duplicatas e apagar vazias.

## 8. Riscos

| Risco | Mitigação |
|-------|-----------|
| Cota Google Drive API | Throttle, retry, inventário/hash incremental |
| Hash lento / arquivos grandes | Cache local; priorizar size>0 e grupos size-iguais antes de hashear |
| Trash da “cópia errada” | Regra de keep explícita + CSV editável + dry-run |
| Docs nativos sem hash | Fora do trash automático |
| Renomear link compartilhado | Rename in-place (mesmo file id); avisar no summary |
| Colisão de nomes | Sufixo `_vNN` ou `_dupN` no plano |
| Home git “sujo” | Artefatos em `~/drive-audit/` |

## 9. Próximo passo

Após aprovação desta spec revisada: skill **writing-plans** → plano de implementação passo a passo, depois execução (inventário primeiro).
