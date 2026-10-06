"""Regras de nomenclatura arquivística AAAA-MM-DD_Tipo_Assunto_Versao.ext."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.drive_audit.config import MAX_ASSUNTO, TIPO_KEYWORDS
from src.drive_audit.textutil import normalize_ascii, strip_noise, to_title_ascii

_STANDARD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[A-Za-z]+_[A-Za-z0-9]+_v\d{2}(\.[A-Za-z0-9]+)?$")
_DATE_PATTERNS = (
    re.compile(r"(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})"),
    re.compile(r"(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})"),
    re.compile(r"(?P<d>\d{2})[.-](?P<m>\d{2})[.-](?P<y>\d{4})"),
)
_YEAR_RE = re.compile(r"(?<!\d)(?P<y>20\d{2})(?!\d)")
_COPY_MARKER_RE = re.compile(r"(c[oó]pia|\bcopy\b|\((?P<n>\d+)\))", re.IGNORECASE)
# Data completa (ISO, compacta ou DD-MM-AAAA) extraída à parte: não deve
# repetir dentro do campo Assunto. Ano solto NÃO é removido (ver extract_date).
_DATE_TOKEN_RE = re.compile(r"(?:\d{4}-\d{2}-\d{2}|\d{8}|\d{2}[.-]\d{2}[.-]\d{4})")


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
    sem_data = _DATE_TOKEN_RE.sub(" ", normalize_ascii(stem))
    return to_title_ascii(sem_data)[:MAX_ASSUNTO] or "SemAssunto"


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
