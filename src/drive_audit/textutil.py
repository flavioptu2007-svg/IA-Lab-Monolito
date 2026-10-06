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
