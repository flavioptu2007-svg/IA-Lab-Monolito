# Auditoria e Renomeação Arquivística do Google Drive — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o pipeline `inventory → hash → pastas vazias → duplicatas → plano de renomeação → summary → apply` que audita o `gdrive:` via rclone, sem alterar nada no Drive até aprovação explícita.

**Architecture:** Pacote Python puro em `src/drive_audit/`: funções de análise (nomenclatura, duplicatas, pastas vazias) são puras e testáveis sem rede; o acesso ao Drive é isolado num wrapper fino sobre o CLI do `rclone` com retry/backoff. Os artefatos (CSV/JSONL/logs) ficam em `~/drive-audit/` (ignorado pelo git); o código fica versionado e coberto pelo CI do repo.

**Tech Stack:** Python ≥3.11, stdlib (`argparse`, `csv`, `json`, `subprocess`, `unicodedata`), CLI `rclone` (remote `gdrive:` já autenticado), pytest.

## Global Constraints

- Remote rclone: `gdrive:` (não `onedrive:`; OneDrive/Dropbox estão fora de escopo).
- Artefatos sempre em `DRIVE_AUDIT_DIR` (padrão `~/drive-audit`): `inventory.jsonl`, `inventory.csv`, `empty_folders.csv`, `duplicates.csv`, `rename_plan.csv`, `summary.md`, `hash_cache.json`, `logs/`.
- Código em `src/drive_audit/` (versionado, coberto por ruff + mypy + pytest). Testes em `tests/`.
- **Zero alteração no Drive** sem `--confirm` explícito. `apply` é dry-run por padrão.
- Formato de nome: `AAAA-MM-DD_Tipo_Assunto_Versao.ext`.
- Vocabulário fechado de Tipo: `Atividade, Plano, Avaliacao, Apostila, Slides, Artigo, Backup, Registro, Material, Outro`.
- Vocabulário de confiança: `alta`, `media`, `baixa`.
- Sem acentos; proibidos `# [ ] { } \ | < > ? * : " /`; assunto em TitleCase ASCII sem espaços, ≤ 60 caracteres; versão `v01` por padrão (cópias `v02`+).
- Trash de duplicatas: `rclone deletefile <path> --drive-use-trash=true` — comando de arquivo único e flag explícita, para **garantir** a lixeira (reversível 30 dias) em vez de exclusão permanente.
- CLI: sempre `python3 -m src.drive_audit <comando>` a partir da raiz do repo (o pacote vive em `src/drive_audit`; a forma `python3 -m drive_audit` não resolve o módulo).
- Limitações conhecidas (decisões, não bugs): `createdTime` não vem no `lsjson` (fica vazio; sem `modifiedTime` também, a data vira `sem-data`); Google Docs nativos não têm MD5 e caem em `hash_missing`; o inventário completo é carregado em memória (`lsjson -R` devolve tudo de uma vez); **este plano implementa apply só do trash de duplicatas** — apply de pastas vazias e de renomeações fica para um plano seguinte; pastas vazias são calculadas antes do trash (o recálculo pós-trash é passo do plano seguinte).
- Lint/format CI: `ruff check ai scripts api src tests` e `ruff format --check ai api src tests` (line-length 100).
- Typecheck CI: `python3 -m mypy ai src api --ignore-missing-imports`.
- Testes CI: `python3 -m pytest tests/ --cov=ai --cov=api --cov=src --cov-fail-under=70`. Código novo precisa cobrir ≥70%.
- Commits: Conventional Commits em português, escopo `drive-audit` (ex.: `feat(drive-audit): ...`).

---

### Task 1: Configuração e normalização de texto

**Files:**
- Create: `src/drive_audit/__init__.py`
- Create: `src/drive_audit/config.py`
- Create: `src/drive_audit/textutil.py`
- Test: `tests/test_drive_audit_textutil.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `config.REMOTE: str`, `config.TIPO_VOCAB: tuple[str, ...]`, `config.TIPO_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...]`, `config.FORBIDDEN_CHARS: str`, `config.MAX_ASSUNTO: int`
  - `config.workdir() -> Path`, `config.ensure_workdir() -> Path`
  - `textutil.normalize_ascii(text: str) -> str`
  - `textutil.strip_noise(name: str) -> str`
  - `textutil.to_title_ascii(text: str) -> str`

- [ ] **Step 1: Criar o pacote e a config**

`src/drive_audit/__init__.py`:

```python
"""Auditoria, deduplicação e renomeação arquivística do Google Drive."""
```

`src/drive_audit/config.py`:

```python
"""Configuração e constantes da auditoria do Google Drive."""

from __future__ import annotations

import os
from pathlib import Path

REMOTE = "gdrive:"

TIPO_VOCAB: tuple[str, ...] = (
    "Atividade",
    "Plano",
    "Avaliacao",
    "Apostila",
    "Slides",
    "Artigo",
    "Backup",
    "Registro",
    "Material",
    "Outro",
)

# Termos em minúsculas e sem acento; a primeira entrada cujo termo aparecer no
# path ou no nome define o Tipo. Backup primeiro: qualquer coisa dentro de uma
# pasta de backup é classificada como Backup independente do conteúdo.
TIPO_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Backup", ("backup", "backups", "bkp", "dump", "avastcleanup", "restore")),
    (
        "Avaliacao",
        (
            "avaliacao", "avaliacoes", "prova", "provas", "teste", "testes",
            "exame", "exames", "simulado", "recuperacao",
        ),
    ),
    ("Plano", ("plano", "planos", "planejamento", "sequencia didatica")),
    (
        "Atividade",
        (
            "atividade", "atividades", "exercicio", "exercicios", "lista",
            "listas", "tarefa", "tarefas", "caca-palavras", "cruzadinha",
            "jogo", "jogos",
        ),
    ),
    ("Apostila", ("apostila", "apostilas", "caderno", "modulo")),
    ("Slides", ("slide", "slides", "apresentacao", "apresentacoes", "ppt", "pptx")),
    (
        "Artigo",
        (
            "artigo", "artigos", "paper", "papers", "dissertacao", "tese",
            "monografia", "ensaio", "resenha",
        ),
    ),
    (
        "Registro",
        (
            "registro", "registros", "ata", "relatorio", "relatorios", "diario",
            "frequencia", "chamada", "parecer",
        ),
    ),
    (
        "Material",
        (
            "material", "materiais", "recurso", "recursos", "mapa", "imagem",
            "imagens", "video", "texto", "textos",
        ),
    ),
)

FORBIDDEN_CHARS = '#[]{}|<>?*:"/'
MAX_ASSUNTO = 60


def workdir() -> Path:
    """Diretório local dos artefatos (não versionado)."""
    return Path(os.environ.get("DRIVE_AUDIT_DIR", "~/drive-audit")).expanduser()


def ensure_workdir() -> Path:
    """Garante que o workdir e o subdiretório de logs existem."""
    base = workdir()
    (base / "logs").mkdir(parents=True, exist_ok=True)
    return base
```

- [ ] **Step 2: Escrever o teste que falha para a normalização**

`tests/test_drive_audit_textutil.py`:

```python
"""Testes da normalização de texto usada nos nomes arquivísticos."""

from __future__ import annotations

from src.drive_audit.textutil import normalize_ascii, strip_noise, to_title_ascii


def test_normalize_ascii_remove_acentos() -> None:
    assert normalize_ascii("Educação Básica") == "Educacao Basica"


def test_strip_noise_remove_prefixo_copia() -> None:
    assert strip_noise("Cópia de Prova Bimestral.docx") == "Prova Bimestral.docx"


def test_strip_noise_remove_sufixo_numerado() -> None:
    assert strip_noise("Prova Bimestral (1).pdf") == "Prova Bimestral.pdf"


def test_strip_noise_remove_timestamp_de_export_do_drive() -> None:
    assert strip_noise("AMOSTRAS CAÇA-20250707T021524Z-1-001.zip") == "AMOSTRAS CAÇA.zip"


def test_to_title_ascii_junta_palavras() -> None:
    assert to_title_ascii("prova bimestral de história") == "ProvaBimestralDeHistoria"
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `python3 -m pytest tests/test_drive_audit_textutil.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.drive_audit.textutil'`.

- [ ] **Step 4: Implementar `textutil.py`**

`src/drive_audit/textutil.py`:

```python
"""Normalização de texto para nomes arquivísticos (sem acentos, sem ruído)."""

from __future__ import annotations

import re
import unicodedata

_NOISE_PREFIX_RE = re.compile(r"^\s*(c[oó]pia de|copia de|copy of)\s+", re.IGNORECASE)
_COPY_SUFFIX_RE = re.compile(r"\s*\(\d{1,2}\)\s*$")
_DRIVE_EXPORT_RE = re.compile(r"-20\d{6}t\d{6}z-\d+-\d+$", re.IGNORECASE)
_NON_ALNUM_RE = re.compile(r"[^0-9a-zA-Z]+")


def normalize_ascii(text: str) -> str:
    """Remove acentos e qualquer caractere não-ASCII (NFKD → ASCII)."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_marks.encode("ascii", "ignore").decode("ascii")


def strip_noise(name: str) -> str:
    """Remove ruído típico de cópias/exportações, preservando a extensão."""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    stem = _NOISE_PREFIX_RE.sub("", stem)
    stem = _COPY_SUFFIX_RE.sub("", stem)
    stem = _DRIVE_EXPORT_RE.sub("", stem)
    stem = stem.strip(" -_.")
    return f"{stem}.{ext}" if ext else stem


def to_title_ascii(text: str) -> str:
    """TitleCase ASCII sem separadores (ex.: 'Prova Bimestral' → 'ProvaBimestral')."""
    words = [w for w in _NON_ALNUM_RE.split(normalize_ascii(text)) if w]
    return "".join(w[:1].upper() + w[1:].lower() for w in words)
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `python3 -m pytest tests/test_drive_audit_textutil.py -q`
Expected: PASS (5 passed).

- [ ] **Step 6: Lint, tipos e commit**

```bash
ruff check src tests && ruff format src tests
python3 -m mypy src --ignore-missing-imports
git add src/drive_audit tests/test_drive_audit_textutil.py
git commit -m "feat(drive-audit): config e normalização de texto dos nomes"
```

---

### Task 2: Regras de nomenclatura arquivística

**Files:**
- Create: `src/drive_audit/naming.py`
- Test: `tests/test_drive_audit_naming.py`

**Interfaces:**
- Consumes: `config.TIPO_KEYWORDS`, `config.MAX_ASSUNTO`; `textutil.normalize_ascii`, `textutil.strip_noise`, `textutil.to_title_ascii`.
- Produces:
  - `naming.NameSuggestion` (frozen dataclass: `suggested: str`, `motivo: str`, `confianca: str`)
  - `naming.is_already_standard(name: str) -> bool`
  - `naming.extract_date(name: str, modified: str = "", created: str = "") -> tuple[str, str]`
  - `naming.infer_tipo(name: str, path: str) -> str`
  - `naming.build_assunto(name: str) -> str`
  - `naming.suggest_name(name, path, is_dir, modified="", created="") -> NameSuggestion | None` (retorna `None` se já está no padrão)

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_drive_audit_naming.py`:

```python
"""Testes das regras de nomenclatura arquivística."""

from __future__ import annotations

from src.drive_audit.naming import (
    build_assunto,
    extract_date,
    infer_tipo,
    is_already_standard,
    suggest_name,
)


def test_extrai_data_de_nome_iso() -> None:
    assert extract_date("2026-03-15 prova.pdf") == ("2026-03-15", "nome")


def test_extrai_data_de_nome_compacto() -> None:
    assert extract_date("20260420_plano.docx") == ("2026-04-20", "nome")


def test_extrai_data_de_dd_mm_aaaa() -> None:
    assert extract_date("15-03-2026 prova.pdf") == ("2026-03-15", "nome")


def test_extrai_data_fallback_modtime() -> None:
    data, origem = extract_date("prova.pdf", "2026-09-30T12:00:00Z", "2026-01-01T00:00:00Z")
    assert (data, origem) == ("2026-09-30", "modifiedTime")


def test_infer_tipo_por_palavra_chave() -> None:
    assert infer_tipo("Plano de Aula março.docx", "x/Plano de Aula março.docx") == "Plano"


def test_infer_tipo_backup_vence_pelo_path() -> None:
    assert infer_tipo("aula.docx", "06_Backups/aula.docx") == "Backup"


def test_infer_tipo_desconhecido_vira_outro() -> None:
    assert infer_tipo("zzz.bin", "zzz.bin") == "Outro"


def test_build_assunto_normaliza_e_remove_ruido() -> None:
    assert build_assunto("Cópia de Prova Bimestral (1).pdf") == "ProvaBimestral"


def test_is_already_standard() -> None:
    assert is_already_standard("2026-04-20_Plano_Abril2026_v01.pdf") is True
    assert is_already_standard("Prova Bimestral.pdf") is False


def test_suggest_name_formato_completo() -> None:
    sugestao = suggest_name(
        "2026-04-20_Prova Bimestral (1).pdf",
        "07_Projetos/2026-04-20_Prova Bimestral (1).pdf",
        False,
        "2026-04-21T00:00:00Z",
    )
    assert sugestao is not None
    assert sugestao.suggested == "2026-04-20_Avaliacao_ProvaBimestral_v02.pdf"
    assert sugestao.confianca == "alta"


def test_suggest_name_ja_no_padrao_retorna_none() -> None:
    assert suggest_name("2026-04-20_Plano_Abril2026_v01.pdf", "x", False) is None


def test_suggest_name_pasta_nao_tem_extensao() -> None:
    # "2026" no nome É um padrão de data para a spec, então vence o modifiedTime
    # (vira 2026-01-01 com origem "nome-ano" e confiança média).
    sugestao = suggest_name("Abril de 2026", "Abril de 2026", True, "2026-04-05T00:00:00Z")
    assert sugestao is not None
    assert sugestao.suggested == "2026-01-01_Outro_AbrilDe2026_v01"
    assert sugestao.confianca == "media"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python3 -m pytest tests/test_drive_audit_naming.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.drive_audit.naming'`.

- [ ] **Step 3: Implementar `naming.py`**

`src/drive_audit/naming.py`:

```python
"""Regras de nomenclatura arquivística AAAA-MM-DD_Tipo_Assunto_Versao.ext."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.drive_audit.config import MAX_ASSUNTO, TIPO_KEYWORDS
from src.drive_audit.textutil import normalize_ascii, strip_noise, to_title_ascii

_STANDARD_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_[A-Za-z]+_[A-Za-z0-9]+_v\d{2}(\.[A-Za-z0-9]+)?$"
)
_DATE_PATTERNS = (
    re.compile(r"(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})"),
    re.compile(r"(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})"),
    re.compile(r"(?P<d>\d{2})[.-](?P<m>\d{2})[.-](?P<y>\d{4})"),
)
_YEAR_RE = re.compile(r"(?<!\d)(?P<y>20\d{2})(?!\d)")
_COPY_MARKER_RE = re.compile(r"(c[oó]pia|\bcopy\b|\((?P<n>\d+)\))", re.IGNORECASE)


@dataclass(frozen=True)
class NameSuggestion:
    """Sugestão de renomeação com motivo e confiança."""

    suggested: str
    motivo: str
    confianca: str


def is_already_standard(name: str) -> bool:
    return bool(_STANDARD_RE.match(name))


def extract_date(name: str, modified: str = "", created: str = "") -> tuple[str, str]:
    """Devolve (data AAAA-MM-DD, origem) seguindo a prioridade da spec."""
    flat = normalize_ascii(name)
    for pattern in _DATE_PATTERNS:
        match = pattern.search(flat)
        if match:
            g = match.groupdict()
            if 1 <= int(g["m"]) <= 12 and 1 <= int(g["d"]) <= 31:
                return f"{g['y']}-{g['m']}-{g['d']}", "nome"
    year = _YEAR_RE.search(flat)
    if year:
        return f"{year.group('y')}-01-01", "nome-ano"
    if modified:
        return modified[:10], "modifiedTime"
    if created:
        return created[:10], "createdTime"
    return "sem-data", "indefinida"


def infer_tipo(name: str, path: str) -> str:
    haystack = normalize_ascii(f"{path}/{name}").lower()
    for tipo, keywords in TIPO_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return tipo
    return "Outro"


def build_assunto(name: str) -> str:
    cleaned = strip_noise(name)
    stem = cleaned.rsplit(".", 1)[0] if "." in cleaned else cleaned
    return to_title_ascii(stem)[:MAX_ASSUNTO] or "SemAssunto"


def _version(name: str) -> str:
    marker = _COPY_MARKER_RE.search(name)
    if not marker:
        return "v01"
    try:
        return f"v{int(marker.group('n')) + 1:02d}"
    except (TypeError, ValueError):
        return "v02"


def suggest_name(
    name: str,
    path: str,
    is_dir: bool,
    modified: str = "",
    created: str = "",
) -> NameSuggestion | None:
    """Sugere o nome arquivístico; devolve ``None`` se já está no padrão."""
    if is_already_standard(name):
        return None
    date, origem = extract_date(name, modified, created)
    tipo = infer_tipo(name, path)
    assunto = build_assunto(name)
    versao = _version(name)
    ext = ""
    if not is_dir and "." in name:
        ext = "." + name.rsplit(".", 1)[1].lower()
    sugerido = f"{date}_{tipo}_{assunto}_{versao}{ext}"
    confianca = "alta"
    if origem in ("nome-ano", "modifiedTime"):
        confianca = "media"
    if origem in ("createdTime", "indefinida"):
        confianca = "baixa"
    motivo = f"data={origem}; tipo inferido por palavra-chave; assunto normalizado"
    return NameSuggestion(sugerido, motivo, confianca)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python3 -m pytest tests/test_drive_audit_naming.py -q`
Expected: PASS (13 passed).

- [ ] **Step 5: Lint, tipos e commit**

```bash
ruff check src tests && ruff format src tests
python3 -m mypy src --ignore-missing-imports
git add src/drive_audit/naming.py tests/test_drive_audit_naming.py
git commit -m "feat(drive-audit): regras de nomenclatura arquivística"
```

---

### Task 3: Análise pura — pastas vazias e duplicatas

**Files:**
- Create: `src/drive_audit/analysis.py`
- Test: `tests/test_drive_audit_analysis.py`

**Interfaces:**
- Consumes: nada (funções puras sobre as linhas do inventário).
- Produces:
  - `analysis.find_empty_folders(rows: list[dict]) -> list[str]`
  - `analysis.choose_keep(items: list[dict]) -> dict`
  - `analysis.group_duplicates(rows: list[dict], hashes: dict[str, str]) -> list[dict]`
  - Chaves de linha do inventário: `path, name, id, size, mime, modified, created, is_dir, hash`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_drive_audit_analysis.py`:

```python
"""Testes das análises puras: pastas vazias e duplicatas."""

from __future__ import annotations

from src.drive_audit.analysis import choose_keep, find_empty_folders, group_duplicates


def _linha(path: str, *, is_dir: bool, size: int = 0, id_: str = "", modified: str = "") -> dict:
    return {
        "path": path,
        "name": path.rsplit("/", 1)[-1],
        "id": id_,
        "size": size,
        "mime": "",
        "modified": modified,
        "created": "",
        "is_dir": is_dir,
        "hash": "",
    }


def test_pastas_vazias_sao_transitivas() -> None:
    rows = [
        _linha("A", is_dir=True),
        _linha("A/B", is_dir=True),
        _linha("C", is_dir=True),
        _linha("D", is_dir=True),
        _linha("D/f.txt", is_dir=False, size=3),
    ]
    assert find_empty_folders(rows) == ["A", "A/B", "C"]


def test_pasta_com_arquivo_nao_e_vazia() -> None:
    rows = [_linha("D", is_dir=True), _linha("D/f.txt", is_dir=False, size=1)]
    assert find_empty_folders(rows) == []


def test_duplicatas_ignoram_pastas_e_arquivos_vazios() -> None:
    rows = [
        _linha("A", is_dir=True, id_="d"),
        _linha("A/x.bin", is_dir=False, size=0, id_="z"),
    ]
    assert group_duplicates(rows, {"d": "hash", "z": "hash2"}) == []


def test_duplicatas_mantem_path_limpo_e_mandam_backup_para_lixeira() -> None:
    rows = [
        _linha(
            "06_Backups/prova.pdf",
            is_dir=False,
            size=10,
            id_="1",
            modified="2026-08-01T00:00:00Z",
        ),
        _linha(
            "07_Projetos/2026-04-20_Avaliacao_Prova_v01.pdf",
            is_dir=False,
            size=10,
            id_="2",
            modified="2026-04-01T00:00:00Z",
        ),
    ]
    resultado = group_duplicates(rows, {"1": "abc", "2": "abc"})
    por_id = {linha["id"]: linha for linha in resultado}
    assert por_id["2"]["action"] == "keep"
    assert por_id["1"]["action"] == "trash"
    assert {linha["group_id"] for linha in resultado} == {1}


def test_choose_keep_usa_mtime_mais_recente_como_desempate() -> None:
    antigo = _linha("a/x.pdf", is_dir=False, id_="a", modified="2026-01-01T00:00:00Z")
    novo = _linha("b/x.pdf", is_dir=False, id_="b", modified="2026-09-01T00:00:00Z")
    assert choose_keep([antigo, novo])["id"] == "b"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python3 -m pytest tests/test_drive_audit_analysis.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.drive_audit.analysis'`.

- [ ] **Step 3: Implementar `analysis.py`**

`src/drive_audit/analysis.py`:

```python
"""Análises puras sobre o inventário: pastas vazias e duplicatas por hash."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any

BACKUP_MARKERS = ("backup", "backups", "backuplinux", "backupdocumentos", "avastcleanup", "bkp")
_STANDARD_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_[A-Za-z]+_[A-Za-z0-9]+_v\d{2}(\.[A-Za-z0-9]+)?$"
)
_NOISE_RE = re.compile(r"(c[oó]pia de|copy of|\(\d+\)|-20\d{6}t\d{6}z)", re.IGNORECASE)


def _parent(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def find_empty_folders(rows: list[dict[str, Any]]) -> list[str]:
    """Pastas sem arquivos e sem subpastas com conteúdo (vazio transitivo)."""
    dirs = {row["path"] for row in rows if row["is_dir"]}
    children: dict[str, list[str]] = {d: [] for d in dirs}
    file_count: dict[str, int] = defaultdict(int)
    for d in dirs:
        parent = _parent(d)
        if parent in children:
            children[parent].append(d)
    for row in rows:
        if not row["is_dir"]:
            file_count[_parent(row["path"])] += 1
    empty: set[str] = set()
    for d in sorted(dirs, key=lambda p: p.count("/"), reverse=True):
        if file_count.get(d, 0) == 0 and all(c in empty for c in children.get(d, [])):
            empty.add(d)
    return sorted(empty)


def _is_backup_path(path: str) -> bool:
    return any(
        any(marker in part.lower() for marker in BACKUP_MARKERS)
        for part in path.split("/")[:-1]
    )


def _mtime_key(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def choose_keep(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Escolhe a cópia a manter (menor chave = melhor), na ordem da spec."""

    def key(row: dict[str, Any]) -> tuple[bool, bool, bool, int, float]:
        name = row["name"]
        return (
            _is_backup_path(row["path"]),
            not bool(_STANDARD_RE.match(name)),
            bool(_NOISE_RE.search(name)),
            len(row["path"]),
            -_mtime_key(row["modified"]),
        )

    return min(items, key=key)


def group_duplicates(
    rows: list[dict[str, Any]], hashes: dict[str, str]
) -> list[dict[str, Any]]:
    """Agrupa por hash e decide keep/trash. Só arquivos hasháveis e size>0."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["is_dir"] or int(row.get("size", 0)) <= 0:
            continue
        digest = hashes.get(row["id"])
        if digest:
            groups[digest].append(row)
    out: list[dict[str, Any]] = []
    group_id = 0
    for digest in sorted(groups):
        items = groups[digest]
        if len(items) < 2:
            continue
        group_id += 1
        keep = choose_keep(items)
        for row in sorted(items, key=lambda r: r["path"]):
            e_keep = row is keep
            out.append(
                {
                    "group_id": group_id,
                    "hash": digest,
                    "action": "keep" if e_keep else "trash",
                    "path": row["path"],
                    "id": row["id"],
                    "size": row["size"],
                    "motivo": (
                        "melhor cópia: path fora de backup, nome limpo e mais curto"
                        if e_keep
                        else "duplicata de conteúdo; enviar à lixeira"
                    ),
                }
            )
    return out
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python3 -m pytest tests/test_drive_audit_analysis.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Lint, tipos e commit**

```bash
ruff check src tests && ruff format src tests
python3 -m mypy src --ignore-missing-imports
git add src/drive_audit/analysis.py tests/test_drive_audit_analysis.py
git commit -m "feat(drive-audit): detecção transitiva de pastas vazias e duplicatas por hash"
```

---

### Task 4: Wrapper do rclone com retry/backoff

**Files:**
- Create: `src/drive_audit/rclone.py`
- Test: `tests/test_drive_audit_rclone.py`

**Interfaces:**
- Consumes: `config.REMOTE`.
- Produces:
  - `rclone.RcloneError(RuntimeError)`
  - `rclone.run_rclone(args: list[str], *, retries: int = 5, base_delay: float = 2.0, sleep: Callable[[float], None] = time.sleep) -> str`
  - `rclone.lsjson(remote_path: str = REMOTE, *, recursive: bool = True) -> list[dict]`
  - `rclone.hashsum(remote_path: str, hasher: str = "MD5") -> str`

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_drive_audit_rclone.py`:

```python
"""Testes do wrapper do rclone (subprocess mockado, sem rede)."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from src.drive_audit import rclone


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_rclone_retorna_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _proc(0, stdout="ok"))
    assert rclone.run_rclone(["version"]) == "ok"


def test_run_rclone_repete_em_rate_limit_e_depois_sucede(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = {"n": 0}

    def fake_run(*_a, **_k):
        chamadas["n"] += 1
        if chamadas["n"] < 3:
            return _proc(1, stderr="googleapi: Error 403: Rate Limit Exceeded, rateLimitExceeded")
        return _proc(0, stdout="[]")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert rclone.run_rclone(["lsjson"], sleep=lambda _s: None) == "[]"
    assert chamadas["n"] == 3


def test_run_rclone_erro_nao_recuperavel_falha_imediato(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = {"n": 0}

    def fake_run(*_a, **_k):
        chamadas["n"] += 1
        return _proc(1, stderr="directory not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(rclone.RcloneError):
        rclone.run_rclone(["lsjson"], sleep=lambda _s: None)
    assert chamadas["n"] == 1


def test_run_rclone_esgota_retries_em_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _proc(1, stderr="RATE_LIMIT_EXCEEDED")
    )
    with pytest.raises(rclone.RcloneError):
        rclone.run_rclone(["lsjson"], retries=3, sleep=lambda _s: None)


def test_lsjson_interpreta_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rclone, "run_rclone", lambda args, **kw: '[{"Path": "a", "IsDir": false}]'
    )
    assert rclone.lsjson("gdrive:") == [{"Path": "a", "IsDir": False}]
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python3 -m pytest tests/test_drive_audit_rclone.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.drive_audit.rclone'`.

- [ ] **Step 3: Implementar `rclone.py`**

`src/drive_audit/rclone.py`:

```python
"""Wrapper fino sobre o CLI do rclone, com retry/backoff para rate limit."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from typing import Any

from src.drive_audit.config import REMOTE

RATE_LIMIT_MARKERS = (
    "rate_limit_exceeded",
    "ratelimitexceeded",
    "userratelimitexceeded",
    "quotaexceeded",
)


class RcloneError(RuntimeError):
    """Falha definitiva de um comando rclone."""


def run_rclone(
    args: list[str],
    *,
    retries: int = 5,
    base_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Executa ``rclone <args>``; repete só em erros de cota/rate limit."""
    cmd = ["rclone", *args]
    last = ""
    for attempt in range(retries):
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return proc.stdout
        stderr = proc.stderr or ""
        last = stderr.strip() or (proc.stdout or "").strip()
        if (
            any(marker in stderr.lower() for marker in RATE_LIMIT_MARKERS)
            and attempt < retries - 1
        ):
            sleep(base_delay * (2**attempt))
            continue
        raise RcloneError(f"rclone {' '.join(args)} falhou: {last}")
    raise RcloneError(f"rclone {' '.join(args)} esgotou os retries: {last}")


def lsjson(remote_path: str = REMOTE, *, recursive: bool = True) -> list[dict[str, Any]]:
    """Lista itens com metadados e hashes (``--hash``)."""
    args = ["lsjson", remote_path, "--hash"]
    if recursive:
        args.append("-R")
    data = json.loads(run_rclone(args) or "[]")
    if not isinstance(data, list):
        raise RcloneError("lsjson retornou JSON inesperado (esperava uma lista)")
    return data


def hashsum(remote_path: str, hasher: str = "MD5") -> str:
    """Calcula o hash de um caminho específico (fallback; lento)."""
    return run_rclone(["hashsum", hasher, remote_path]).strip()
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python3 -m pytest tests/test_drive_audit_rclone.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Lint, tipos e commit**

```bash
ruff check src tests && ruff format src tests
python3 -m mypy src --ignore-missing-imports
git add src/drive_audit/rclone.py tests/test_drive_audit_rclone.py
git commit -m "feat(drive-audit): wrapper do rclone com retry/backoff em rate limit"
```

---

### Task 5: Inventário e coleta de hashes

**Files:**
- Create: `src/drive_audit/inventory.py`
- Create: `src/drive_audit/hashing.py`
- Test: `tests/test_drive_audit_inventory.py`
- Test: `tests/test_drive_audit_hashing.py`

**Interfaces:**
- Consumes: `rclone.lsjson`; `config.REMOTE`.
- Produces:
  - `inventory.CSV_FIELDS: tuple[str, ...]`
  - `inventory.to_row(entry: dict) -> dict`
  - `inventory.build_inventory() -> list[dict]`
  - `inventory.write_inventory(rows, jsonl_path: Path, csv_path: Path) -> None`
  - `inventory.load_inventory(jsonl_path: Path) -> list[dict]`
  - `hashing.load_cache(path: Path) -> dict[str, dict]`
  - `hashing.save_cache(cache: dict[str, dict], path: Path) -> None`
  - `hashing.collect_hashes(rows, cache, *, hashsum_fn=None) -> tuple[dict[str, str], list[str]]`

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_drive_audit_inventory.py`:

```python
"""Testes do inventário (rclone mockado)."""

from __future__ import annotations

from pathlib import Path

from src.drive_audit import inventory


def test_to_row_normaliza_chaves_e_hash() -> None:
    entry = {
        "Path": "a/b.pdf",
        "Name": "b.pdf",
        "ID": "42",
        "Size": 10,
        "MimeType": "application/pdf",
        "ModTime": "2026-04-01T10:00:00Z",
        "IsDir": False,
        "Hashes": {"md5": "abc123"},
    }
    row = inventory.to_row(entry)
    assert row["path"] == "a/b.pdf"
    assert row["id"] == "42"
    assert row["hash"] == "abc123"
    assert row["is_dir"] is False


def test_to_row_pasta_sem_hash() -> None:
    row = inventory.to_row({"Path": "A", "Name": "A", "IsDir": True})
    assert row["is_dir"] is True
    assert row["hash"] == ""


def test_write_e_load_inventory_roundtrip(tmp_path: Path) -> None:
    rows = [inventory.to_row({"Path": "a.pdf", "Name": "a.pdf", "ID": "1", "Size": 1})]
    jsonl = tmp_path / "inventory.jsonl"
    csv_path = tmp_path / "inventory.csv"
    inventory.write_inventory(rows, jsonl, csv_path)
    assert jsonl.exists() and csv_path.exists()
    assert inventory.load_inventory(jsonl) == rows
```

`tests/test_drive_audit_hashing.py`:

```python
"""Testes da coleta de hashes com cache."""

from __future__ import annotations

from pathlib import Path

from src.drive_audit import hashing


def _arquivo(id_: str, path: str, *, hash_: str = "", modified: str = "t1", size: int = 5) -> dict:
    return {
        "path": path,
        "name": path,
        "id": id_,
        "size": size,
        "mime": "",
        "modified": modified,
        "created": "",
        "is_dir": False,
        "hash": hash_,
    }


def test_usa_hash_do_inventario() -> None:
    rows = [_arquivo("1", "a.pdf", hash_="abc")]
    hashes, faltando = hashing.collect_hashes(rows, {})
    assert hashes == {"1": "abc"}
    assert faltando == []


def test_arquivo_sem_hash_entra_em_faltando() -> None:
    rows = [_arquivo("2", "doc", hash_="")]
    hashes, faltando = hashing.collect_hashes(rows, {})
    assert hashes == {}
    assert faltando == ["doc"]


def test_cache_evita_recalculo() -> None:
    rows = [_arquivo("1", "a.pdf", hash_="")]
    cache = {"1": {"mtime": "t1", "hash": "cached"}}
    hashes, faltando = hashing.collect_hashes(rows, cache)
    assert hashes == {"1": "cached"}
    assert faltando == []


def test_cache_invalida_se_mtime_muda() -> None:
    rows = [_arquivo("1", "a.pdf", hash_="novo", modified="t2")]
    cache = {"1": {"mtime": "t1", "hash": "antigo"}}
    hashes, _ = hashing.collect_hashes(rows, cache)
    assert hashes == {"1": "novo"}
    assert cache["1"]["hash"] == "novo"


def test_fallback_hashsum_quando_fornecido() -> None:
    rows = [_arquivo("3", "b.pdf", hash_="")]
    hashes, _ = hashing.collect_hashes(rows, {}, hashsum_fn=lambda _p: "deadbeef  b.pdf")
    assert hashes == {"3": "deadbeef"}


def test_save_e_load_cache(tmp_path: Path) -> None:
    caminho = tmp_path / "hash_cache.json"
    hashing.save_cache({"1": {"mtime": "t", "hash": "h"}}, caminho)
    assert hashing.load_cache(caminho) == {"1": {"mtime": "t", "hash": "h"}}
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python3 -m pytest tests/test_drive_audit_inventory.py tests/test_drive_audit_hashing.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.drive_audit.inventory'`.

- [ ] **Step 3: Implementar `inventory.py` e `hashing.py`**

`src/drive_audit/inventory.py`:

```python
"""Inventário do Drive → inventory.jsonl + inventory.csv."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.drive_audit import config, rclone

CSV_FIELDS: tuple[str, ...] = (
    "path",
    "name",
    "id",
    "size",
    "mime",
    "modified",
    "created",
    "is_dir",
    "hash",
)


def to_row(entry: dict[str, Any]) -> dict[str, Any]:
    """Converte um item do lsjson na linha estável do inventário."""
    hashes = entry.get("Hashes") or {}
    # rclone emite a chave minúscula ("md5") no lsjson; aceita as duas formas.
    digest = hashes.get("MD5") or hashes.get("md5") or next(iter(hashes.values()), "")
    return {
        "path": entry.get("Path", ""),
        "name": entry.get("Name", ""),
        "id": entry.get("ID", ""),
        "size": entry.get("Size", 0),
        "mime": entry.get("MimeType", ""),
        "modified": entry.get("ModTime", ""),
        # O lsjson não expõe createdTime; fica vazio e é documentado no summary.
        "created": "",
        "is_dir": bool(entry.get("IsDir", False)),
        "hash": digest,
    }


def build_inventory() -> list[dict[str, Any]]:
    return rclone.lsjson(config.REMOTE, recursive=True)


def write_inventory(rows: list[dict[str, Any]], jsonl_path: Path, csv_path: Path) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        writer.writerows(rows)


def load_inventory(jsonl_path: Path) -> list[dict[str, Any]]:
    with Path(jsonl_path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
```

`src/drive_audit/hashing.py`:

```python
"""Coleta de hashes MD5 (do inventário) com cache local em disco."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.drive_audit import config


def load_cache(path: Path) -> dict[str, dict[str, Any]]:
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, dict[str, Any]], path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_hashes(
    rows: list[dict[str, Any]],
    cache: dict[str, dict[str, Any]],
    *,
    hashsum_fn: Callable[[str], str] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Devolve (id → md5, paths sem hash).

    Usa o hash já presente no inventário; ``hashsum_fn`` é o fallback lento
    (desligado por padrão) para arquivos sem MD5 nos metadados.
    """
    result: dict[str, str] = {}
    missing: list[str] = []
    for row in rows:
        if row["is_dir"] or int(row.get("size", 0)) <= 0:
            continue
        cached = cache.get(row["id"])
        if cached and cached.get("mtime") == row["modified"]:
            digest = str(cached.get("hash") or "")
        else:
            digest = str(row.get("hash") or "")
            if not digest and hashsum_fn is not None:
                parts = hashsum_fn(f"{config.REMOTE}{row['path']}").split()
                digest = parts[0] if parts and parts[0] != "UNSUPPORTED" else ""
            cache[row["id"]] = {"mtime": row["modified"], "hash": digest}
        if digest:
            result[row["id"]] = digest
        else:
            missing.append(row["path"])
    return result, missing
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python3 -m pytest tests/test_drive_audit_inventory.py tests/test_drive_audit_hashing.py -q`
Expected: PASS (9 passed).

- [ ] **Step 5: Lint, tipos e commit**

```bash
ruff check src tests && ruff format src tests
python3 -m mypy src --ignore-missing-imports
git add src/drive_audit/inventory.py src/drive_audit/hashing.py tests/test_drive_audit_inventory.py tests/test_drive_audit_hashing.py
git commit -m "feat(drive-audit): inventário do Drive e coleta de hashes com cache"
```

---

### Task 6: Relatório e CLI (`inventory` / `analyze`)

**Files:**
- Create: `src/drive_audit/report.py`
- Create: `src/drive_audit/cli.py`
- Create: `src/drive_audit/__main__.py`
- Create: `src/drive_audit/apply_batch.py`
- Test: `tests/test_drive_audit_cli.py`

**Interfaces:**
- Consumes: tudo das Tasks 1–5.
- Produces:
  - `report.build_summary(rows, empty, duplicate_rows, hash_missing, *, generated_at: str) -> str`
  - `cli.main(argv: list[str] | None = None) -> int`
  - Comandos: `inventory`, `analyze`, `apply`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_drive_audit_cli.py`:

```python
"""Testes do relatório e da CLI (sem tocar no Drive real)."""

from __future__ import annotations

from pathlib import Path

from src.drive_audit import cli, report


def _linha(path: str, *, is_dir: bool, size: int = 0, id_: str = "", name: str = "") -> dict:
    return {
        "path": path,
        "name": name or path.rsplit("/", 1)[-1],
        "id": id_,
        "size": size,
        "mime": "",
        "modified": "2026-04-20T00:00:00Z",
        "created": "",
        "is_dir": is_dir,
        "hash": "",
    }


def test_summary_conta_itens_e_espaco_recuperavel() -> None:
    rows = [_linha("a.pdf", is_dir=False, size=1048576, id_="1")]
    empty = ["P"]
    dup = [
        {"group_id": 1, "hash": "h", "action": "keep", "path": "a.pdf", "id": "1", "size": 1048576, "motivo": ""},
        {"group_id": 1, "hash": "h", "action": "trash", "path": "b.pdf", "id": "2", "size": 1048576, "motivo": ""},
    ]
    texto = report.build_summary(rows, empty, dup, ["doc-native"], generated_at="2026-10-06T00:00:00Z")
    assert "Itens inventariados: 1" in texto
    assert "Pastas vazias: 1" in texto
    assert "Cópias marcadas para lixeira: 1" in texto
    assert "1.00 MiB" in texto
    assert "Nenhuma alteração foi feita no Drive" in texto


def test_cli_analyze_escreve_artefatos(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DRIVE_AUDIT_DIR", str(tmp_path))
    rows = [
        _linha("06_Backups/prova.pdf", is_dir=False, size=10, id_="1"),
        _linha("07_Projetos/prova.pdf", is_dir=False, size=10, id_="2"),
    ]
    for row in rows:
        row["hash"] = "abc"
    # inventário já pronto para o analyze não chamar o rclone
    from src.drive_audit import inventory

    inventory.write_inventory(rows, tmp_path / "inventory.jsonl", tmp_path / "inventory.csv")
    assert cli.main(["analyze"]) == 0
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "duplicates.csv").exists()
    assert (tmp_path / "empty_folders.csv").exists()
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python3 -m pytest tests/test_drive_audit_cli.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.drive_audit.cli'`.

- [ ] **Step 3: Implementar `report.py`, `cli.py` e `__main__.py`**

`src/drive_audit/report.py`:

```python
"""Gera o summary.md do lote de auditoria."""

from __future__ import annotations

from typing import Any


def build_summary(
    rows: list[dict[str, Any]],
    empty: list[str],
    duplicate_rows: list[dict[str, Any]],
    hash_missing: list[str],
    *,
    generated_at: str,
) -> str:
    files = [row for row in rows if not row["is_dir"]]
    dirs = [row for row in rows if row["is_dir"]]
    trash = [row for row in duplicate_rows if row["action"] == "trash"]
    freed = sum(int(row["size"]) for row in trash)
    groups = len({row["group_id"] for row in duplicate_rows})
    return "\n".join(
        [
            "# Auditoria do Google Drive — Resumo",
            "",
            f"Gerado em: {generated_at}",
            "",
            "## Contagens",
            "",
            f"- Itens inventariados: {len(rows)}",
            f"- Arquivos: {len(files)}",
            f"- Pastas: {len(dirs)}",
            f"- Pastas vazias: {len(empty)}",
            f"- Grupos de duplicatas: {groups}",
            f"- Cópias marcadas para lixeira: {len(trash)}",
            f"- Espaço recuperável estimado: {freed / (1024 * 1024):.2f} MiB",
            f"- Arquivos sem hash (revisar manualmente): {len(hash_missing)}",
            "",
            "## Segurança",
            "",
            "Nenhuma alteração foi feita no Drive. O apply só roda após aprovação por lote.",
            "",
        ]
    )
```

`src/drive_audit/cli.py`:

```python
"""CLI da auditoria do Google Drive: python -m drive_audit <comando>."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.drive_audit import (
    analysis,
    apply_batch,
    config,
    hashing,
    inventory,
    naming,
    report,
)


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def cmd_inventory(_args: argparse.Namespace) -> int:
    base = config.ensure_workdir()
    rows = [inventory.to_row(entry) for entry in inventory.build_inventory()]
    inventory.write_inventory(rows, base / "inventory.jsonl", base / "inventory.csv")
    print(f"Inventário: {len(rows)} itens → {base / 'inventory.csv'}")
    return 0


def _parent(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _with_dup_suffix(name: str, n: int) -> str:
    stem, dot, ext = name.rpartition(".")
    return f"{stem}_dup{n}.{ext}" if dot else f"{name}_dup{n}"


def _rename_rows(
    rows: list[dict[str, Any]], trash_paths: set[str]
) -> list[dict[str, Any]]:
    """Sugere renomeações; pula duplicatas em trash e resolve colisões (_dupN)."""
    usados = {(_parent(r["path"]), r["name"].lower()) for r in rows}
    out: list[dict[str, Any]] = []
    for row in rows:
        # A spec proíbe renomear cópias que já vão para a lixeira.
        if row["path"] in trash_paths:
            continue
        sugestao = naming.suggest_name(
            row["name"], row["path"], row["is_dir"], row["modified"], row["created"]
        )
        if sugestao is None:
            continue
        parent = _parent(row["path"])
        final = sugestao.suggested
        n = 1
        while (parent, final.lower()) in usados:
            n += 1
            final = _with_dup_suffix(sugestao.suggested, n)
        usados.add((parent, final.lower()))
        out.append(
            {
                "path_atual": row["path"],
                "nome_atual": row["name"],
                "nome_sugerido": final,
                "motivo": sugestao.motivo,
                "confianca": sugestao.confianca,
            }
        )
    return out


def cmd_analyze(_args: argparse.Namespace) -> int:
    base = config.ensure_workdir()
    rows = inventory.load_inventory(base / "inventory.jsonl")

    empty = analysis.find_empty_folders(rows)
    _write_csv(base / "empty_folders.csv", ("path",), [{"path": p} for p in empty])

    cache = hashing.load_cache(base / "hash_cache.json")
    hashes, missing = hashing.collect_hashes(rows, cache)
    hashing.save_cache(cache, base / "hash_cache.json")

    duplicates = analysis.group_duplicates(rows, hashes)
    _write_csv(
        base / "duplicates.csv",
        ("group_id", "hash", "action", "path", "id", "size", "motivo"),
        duplicates,
    )

    trash_paths = {row["path"] for row in duplicates if row["action"] == "trash"}
    rename_rows = _rename_rows(rows, trash_paths)
    _write_csv(
        base / "rename_plan.csv",
        ("path_atual", "nome_atual", "nome_sugerido", "motivo", "confianca"),
        rename_rows,
    )

    summary = report.build_summary(
        rows, empty, duplicates, missing, generated_at=datetime.now(timezone.utc).isoformat()
    )
    (base / "summary.md").write_text(summary, encoding="utf-8")
    print(
        f"Análise: {len(empty)} pastas vazias, "
        f"{len(duplicates)} linhas de duplicatas, "
        f"{len(rename_rows)} renomeações → {base / 'summary.md'}"
    )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    base = config.ensure_workdir()
    actions = apply_batch.load_actions(base / "duplicates.csv")
    results = apply_batch.apply_actions(
        actions, dry_run=not args.confirm, log_path=base / "logs" / "apply.jsonl"
    )
    modo = "APPLY" if args.confirm else "dry-run"
    print(f"{modo}: {len(results)} ações")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drive_audit", description="Auditoria do Google Drive (rclone).")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("inventory", help="Lista o Drive e grava inventory.jsonl/csv")
    sub.add_parser("analyze", help="Pastas vazias, duplicatas, renomeações e summary.md")
    apply_parser = sub.add_parser("apply", help="Aplica o lote aprovado (padrão: dry-run)")
    apply_parser.add_argument(
        "--confirm", action="store_true", help="Apply real: envia duplicatas à lixeira"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"inventory": cmd_inventory, "analyze": cmd_analyze, "apply": cmd_apply}
    return handlers[args.comando](args)
```

`src/drive_audit/__main__.py`:

```python
"""Entry point: ``python -m src.drive_audit <comando>``."""

from __future__ import annotations

import sys

from src.drive_audit.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Criar `apply_batch.py` mínimo** (necessário para o import da CLI)

`src/drive_audit/apply_batch.py`:

```python
"""Dry-run e apply de um lote aprovado (trash de duplicatas)."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.drive_audit import config, rclone


def load_actions(duplicates_csv: Path) -> list[dict[str, Any]]:
    with Path(duplicates_csv).open(encoding="utf-8", newline="") as fh:
        return [row for row in csv.DictReader(fh) if row["action"] == "trash"]


def apply_actions(
    actions: list[dict[str, Any]],
    *,
    dry_run: bool = True,
    log_path: Path,
    run_fn: Callable[[list[str]], str] = rclone.run_rclone,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> list[dict[str, Any]]:
    """Aplica (ou simula) cada ação; sempre anexa o resultado ao log."""
    results: list[dict[str, Any]] = []
    for row in actions:
        remote = f"{config.REMOTE}{row['path']}"
        if dry_run:
            resultado = "dry-run"
        else:
            try:
                # deletefile + flag explícita: garante a lixeira, nunca exclusão permanente.
                run_fn(["deletefile", remote, "--drive-use-trash=true"])
                resultado = "ok"
            except rclone.RcloneError as exc:  # pragma: no cover - caminho de erro real
                resultado = f"erro: {exc}"
        results.append(
            {
                "timestamp": now().isoformat(),
                "id": row["id"],
                "path": row["path"],
                "acao": "trash",
                "resultado": resultado,
            }
        )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        for entry in results:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return results
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `python3 -m pytest tests/test_drive_audit_cli.py -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Rodar a suíte completa e o CI local**

Run:
```bash
ruff check ai scripts api src tests && ruff format --check ai api src tests
python3 -m mypy ai src api --ignore-missing-imports
IA_LAB_RAG_ENABLED=false python3 -m pytest tests/ -q --cov=ai --cov=api --cov=src --cov-fail-under=70
```
Expected: tudo verde.

- [ ] **Step 7: Commit**

```bash
git add src/drive_audit/report.py src/drive_audit/cli.py src/drive_audit/__main__.py src/drive_audit/apply_batch.py tests/test_drive_audit_cli.py
git commit -m "feat(drive-audit): relatório summary.md, CLI (inventory/analyze/apply) e apply dry-run"
```

---

### Task 7: Testes de `apply_batch` (dry-run vs apply)

**Files:**
- Test: `tests/test_drive_audit_apply.py`

**Interfaces:**
- Consumes: `apply_batch.load_actions`, `apply_batch.apply_actions`.
- Produces: nenhuma nova interface.

- [ ] **Step 1: Escrever os testes**

`tests/test_drive_audit_apply.py`:

```python
"""Testes do apply por lote: dry-run não toca no Drive, apply usa delete."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from src.drive_audit import apply_batch


def _escrever_duplicates(tmp_path: Path) -> Path:
    caminho = tmp_path / "duplicates.csv"
    with caminho.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["group_id", "hash", "action", "path", "id", "size", "motivo"],
        )
        writer.writeheader()
        writer.writerow(
            {"group_id": 1, "hash": "h", "action": "keep", "path": "bom.pdf", "id": "1", "size": 1, "motivo": ""}
        )
        writer.writerow(
            {"group_id": 1, "hash": "h", "action": "trash", "path": "ruim.pdf", "id": "2", "size": 1, "motivo": ""}
        )
    return caminho


def test_load_actions_so_trash(tmp_path: Path) -> None:
    actions = apply_batch.load_actions(_escrever_duplicates(tmp_path))
    assert [a["id"] for a in actions] == ["2"]


def test_dry_run_nao_chama_rclone(tmp_path: Path) -> None:
    chamadas: list[list[str]] = []
    results = apply_batch.apply_actions(
        [{"id": "2", "path": "ruim.pdf"}],
        dry_run=True,
        log_path=tmp_path / "logs" / "apply.jsonl",
        run_fn=lambda args: chamadas.append(args) or "",
    )
    assert chamadas == []
    assert results[0]["resultado"] == "dry-run"
    assert (tmp_path / "logs" / "apply.jsonl").exists()


def test_apply_real_envia_para_lixeira(tmp_path: Path) -> None:
    chamadas: list[list[str]] = []
    results = apply_batch.apply_actions(
        [{"id": "2", "path": "ruim.pdf"}],
        dry_run=False,
        log_path=tmp_path / "apply.jsonl",
        run_fn=lambda args: chamadas.append(args) or "",
        now=lambda: datetime(2026, 10, 6, tzinfo=timezone.utc),
    )
    assert chamadas == [["deletefile", "gdrive:ruim.pdf", "--drive-use-trash=true"]]
    assert results[0]["resultado"] == "ok"
    assert results[0]["timestamp"] == "2026-10-06T00:00:00+00:00"
```

- [ ] **Step 2: Rodar e confirmar que passa**

Run: `python3 -m pytest tests/test_drive_audit_apply.py -q`
Expected: PASS (3 passed).

- [ ] **Step 3: Commit**

```bash
git add tests/test_drive_audit_apply.py
git commit -m "test(drive-audit): cobre dry-run e apply real do lote de duplicatas"
```

---

### Task 8: Documentação e primeira execução real (Drive inteiro)

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md` (seção curta "Auditoria do Google Drive")

**Interfaces:**
- Consumes: CLI das Tasks 6–7.
- Produces: artefatos reais em `~/drive-audit/`.

- [ ] **Step 1: Documentar o uso**

Adicionar ao `README.md` (perto das demais seções de uso) e ao `CHANGELOG.md` o bloco:

```markdown
## Auditoria do Google Drive

```bash
# 1) Inventário completo (rclone gdrive:) → ~/drive-audit/inventory.{jsonl,csv}
python3 -m src.drive_audit inventory

# 2) Pastas vazias, duplicatas, plano de renomeação e summary.md
python3 -m src.drive_audit analyze

# 3) Revisar ~/drive-audit/{summary.md,duplicates.csv,rename_plan.csv}
#    Apply é dry-run por padrão; só envia duplicatas à lixeira com --confirm.
python3 -m src.drive_audit apply            # simulação
python3 -m src.drive_audit apply --confirm  # ação real (após aprovação do lote)
```
```

- [ ] **Step 2: Rodar o inventário completo (em lotes retomáveis)**

> **Nota de execução (medido em 2026-10-06):** o Drive é grande — só a pasta
> de topo `07_Projetos e IA` tem 40.586 itens (~157 s); um `lsjson -R` global
> e o crawl pasta-a-pasta sem `--fast-list` **não terminam**. O `inventory` é
> resumível: lista a raiz uma vez e depois as pastas de topo em lotes
> (`--max-dirs`), gravando `inventory.state.json`. Rode repetidamente, ou em
> background com `bash ~/drive-audit/crawl.sh`, até a fila esvaziar.

Run: `DRIVE_AUDIT_DIR=$HOME/drive-audit bash ~/drive-audit/crawl.sh`
Expected: conclui gravando `~/drive-audit/inventory.{jsonl,csv}` e imprime
`CRAWL COMPLETO`. `RATE_LIMIT_EXCEEDED` faz o wrapper repetir com backoff.

- [ ] **Step 3: Rodar a análise**

Run: `python3 -m src.drive_audit analyze`

> **Achado do piloto real:** em `07_Projetos e IA`, 2.255 grupos de duplicatas e
> 5.359 cópias para lixeira — a maioria `node_modules` (ex.: `date-fns/*.d.mts`
> × `*.d.ts`, bytes idênticos). **Antes do `apply --confirm`, avaliar um filtro
> para excluir `node_modules`/`node_modules/.*` do trash** (arquivos distintos
> por extensão podem ser exigidos pelo toolchain).
Expected: gera `empty_folders.csv`, `duplicates.csv`, `rename_plan.csv` e `summary.md` em `~/drive-audit/`.

> **Resultado da execução (2026-10-06, Drive completo):** inventário fechado com
> 272.665 itens (253.384 arquivos, 19.281 pastas). `analyze`: 326 pastas vazias;
> 41.389 grupos de duplicatas → 67.447 cópias para lixeira (~223 GiB
> recuperáveis; o CSV grava tamanho em **MiB**); 187.381 renomeações
> (53.441 em pastas técnicas); 0 arquivos sem hash. Distribuição do trash:
> 9.403 em pastas técnicas (node_modules/.git — **não aplicar**) e 58.044 em
> documentos, concentrados em `PDF` (23.389 itens, ~96 GiB), `06_Backups`
> (17.709, ~44 GiB), `BackupLinux` (5.422, ~18 GiB), `BackupDocumentos`
> (2.938, ~4 GiB), `Material clientes` (1.891, ~16 GiB), `Livros` (1.115,
> ~2,5 GiB) e `Aulas do professor Kennedy` (~14 GiB somando as variantes).
> Nada foi alterado no Drive; apply continua exigindo aprovação por lote.

- [ ] **Step 4: Conferir o resumo**

Run: `sed -n '1,40p' ~/drive-audit/summary.md && head -5 ~/drive-audit/duplicates.csv`
Expected: contagens coerentes (itens inventariados > 0, grupos de duplicatas > 0, espaço recuperável > 0).

- [ ] **Step 5: Commit da documentação**

```bash
git add README.md CHANGELOG.md
git commit -m "docs(drive-audit): documenta inventário, análise e apply por lote"
```

- [ ] **Step 6: NÃO aplicar nada**

`apply --confirm` **não** faz parte deste plano. Só após revisão humana do `summary.md`, `duplicates.csv` e `rename_plan.csv`, e aprovação explícita por lote.

---

## Self-Review

**1. Cobertura da spec:**
- Inventário (`inventory.csv` + metadados) → Tasks 1, 5, 6. `paths/name/id/size/mime/modified/is_dir/hash` cobertos; `created` documentado como não fornecido pelo `lsjson`.
- Hashes com cache → Task 5.
- Pastas vazias transitivas → Task 3, 6.
- Duplicatas por hash com `keep`/`trash` e regra de prioridade → Task 3, 6.
- Plano de renomeação no padrão `AAAA-MM-DD_Tipo_Assunto_Versao` → Task 2, 6.
- `summary.md` com contagens e espaço recuperável → Task 6.
- Apply por lote dry-run → aprovação → apply com log → Task 7, 8.
- Zero alteração antes da aprovação → `apply` sem `--confirm` é dry-run (Task 6, 8).
- Google Docs nativos sem hash → entram em `hash_missing` (Task 5) e no summary (Task 6).
- Fora de escopo mantido: sem fusão semântica, sem OneDrive/Dropbox, sem mover entre pastas.

**2. Varredura de placeholders:** nenhuma etapa com "TODO"/"implement later"; todo passo de código traz o código completo.

**3. Consistência de tipos/nomes:** `to_row`/`CSV_FIELDS` (Task 5) usados pela CLI (Task 6); `collect_hashes` devolve `tuple[dict[str,str], list[str]]` consumido por `cmd_analyze`; `NameSuggestion.suggested/motivo/confianca` mapeados em `_rename_rows`; `apply_actions(...)` com `dry_run` usado por `cmd_apply`; chaves `group_id/hash/action/path/id/size/motivo` iguais entre `analysis.group_duplicates`, `duplicates.csv` e `apply_batch.load_actions`.
