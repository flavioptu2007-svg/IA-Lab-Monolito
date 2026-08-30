"""GRP Audit / Preview mode.

Reads the current state of the GRP (context + grades) from a Playwright page,
compares it with data from an Excel spreadsheet, and generates a diff preview.
**Never writes to GRP** — this module is read-only.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from .models import StudentRef

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GrpContext:
    """Context extracted from GRP hidden inputs."""

    school: str
    class_name: str
    subject: str
    period: str
    evaluation: str


@dataclass(frozen=True)
class GrpStudentGrade:
    """A single student grade read from the GRP table."""

    name: str
    value: float | None


@dataclass(frozen=True)
class AuditDiffItem:
    """One difference between Excel and GRP."""

    student: str
    change_type: str  # "new", "changed", "not_found", "not_in_source"
    old_value: float | None = None
    new_value: float | None = None


@dataclass(frozen=True)
class AuditDiff:
    """Aggregated diff between Excel and GRP."""

    items: list[AuditDiffItem] = field(default_factory=list)
    has_changes: bool = False


@dataclass(frozen=True)
class AuditPreview:
    """Full preview of what would change in GRP."""

    context: GrpContext
    diff: AuditDiff
    total_students: int = 0
    changes_count: int = 0
    blocked: bool = False

    @property
    def has_changes(self) -> bool:
        return self.diff.has_changes


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _norm(value: str) -> str:
    """Normalize text for comparison: strip accents, lowercase, collapse whitespace."""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().casefold()


_HIDDEN_FIELDS = {
    "school": ["C. M. E.", "EMEF", "E. M.", "ESCOLA"],
    "class_name": ["ANO", "TURMA", "CLASSE"],
    "subject": ["HISTÓRIA", "MATEMÁTICA", "PORTUGUÊS", "CIÊNCIAS", "GEOGRAFIA", "EDUCAÇÃO", "INGLÊS", "ARTES", "EDUCAÇÃO FÍSICA"],
    "period": ["TRIMESTRE", "BIMESTRE", "SEMESTRE", "PERÍODO"],
    "evaluation": ["AVALIAÇÃO", "AVALIACAO", "PROVA", "AVERBAÇÃO"],
}


def _read_hidden_inputs(page: Any) -> dict[str, str]:
    """Read all hidden input values from the GRP page."""
    inputs = page.locator("input[type='hidden']")
    values = {}
    for i in range(inputs.count()):
        val = inputs.nth(i).get_attribute("value") or ""
        if val.strip():
            values[i] = val.strip()
    return values


def _classify_hidden_value(value: str) -> str | None:
    """Classify a hidden input value into a context field."""
    normalized = _norm(value)
    for field_name, keywords in _HIDDEN_FIELDS.items():
        for keyword in keywords:
            if _norm(keyword) in normalized:
                return field_name
    return None


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def read_grp_context(page: Any) -> GrpContext:
    """Read the GRP context (school, class, subject, period, evaluation)
    from hidden inputs on the current page.
    """
    inputs = _read_hidden_inputs(page)
    classified: dict[str, str] = {}

    for value in inputs.values():
        field_name = _classify_hidden_value(value)
        if field_name and field_name not in classified:
            classified[field_name] = value

    return GrpContext(
        school=classified.get("school", ""),
        class_name=classified.get("class_name", ""),
        subject=classified.get("subject", ""),
        period=classified.get("period", ""),
        evaluation=classified.get("evaluation", ""),
    )


def read_grp_grades(page: Any) -> list[GrpStudentGrade]:
    """Read student names and grades from the GRP table.

    The GRP displays students in a <table> with the student name in the first
    <td> and the grade input in the last <td> of each <tr>.
    """
    result: list[GrpStudentGrade] = []
    rows = page.locator("table tr")
    for i in range(rows.count()):
        row = rows.nth(i)
        cells = row.locator("td")
        if cells.count() < 2:
            continue
        name = cells.first.inner_text().strip()
        if not name:
            continue
        # Grade is in the last cell's input
        inputs = row.locator("input")
        value: float | None = None
        if inputs.count():
            raw = inputs.last.input_value().strip()
            if raw:
                try:
                    value = float(raw.replace(",", "."))
                except ValueError:
                    value = None
        result.append(GrpStudentGrade(name=name, value=value))
    return result


def compare_grades(
    excel_students: list[StudentRef],
    excel_grades: dict[str, float],
    grp_grades: list[GrpStudentGrade],
) -> AuditDiff:
    """Compare Excel grades against GRP grades and return a diff.

    Parameters
    ----------
    excel_students:
        List of students from the Excel file.
    excel_grades:
        Mapping of normalized student name → grade value from Excel.
    grp_grades:
        Grades read from the GRP page.
    """
    items: list[AuditDiffItem] = []
    grp_map = {_norm(g.name): g for g in grp_grades}
    # Normalize excel_grades keys for case-insensitive lookup
    excel_map = {_norm(k): v for k, v in excel_grades.items()}

    # Check each Excel student against GRP
    for student in excel_students:
        norm_name = _norm(student.name)
        excel_val = excel_map.get(norm_name)

        if norm_name not in grp_map:
            items.append(
                AuditDiffItem(
                    student=student.name,
                    change_type="not_found",
                    new_value=excel_val,
                )
            )
            continue

        grp = grp_map[norm_name]
        if grp.value is None and excel_val is not None:
            items.append(
                AuditDiffItem(
                    student=student.name,
                    change_type="new",
                    old_value=None,
                    new_value=excel_val,
                )
            )
        elif excel_val is not None and grp.value != excel_val:
            items.append(
                AuditDiffItem(
                    student=student.name,
                    change_type="changed",
                    old_value=grp.value,
                    new_value=excel_val,
                )
            )

    # Check for students in GRP but not in Excel
    excel_names = {_norm(s.name) for s in excel_students}
    for grp_grade in grp_grades:
        if _norm(grp_grade.name) not in excel_names:
            items.append(
                AuditDiffItem(
                    student=grp_grade.name,
                    change_type="not_in_source",
                    old_value=grp_grade.value,
                )
            )

    return AuditDiff(items=items, has_changes=len(items) > 0)


def generate_audit_preview(
    context: GrpContext,
    excel_students: list[StudentRef],
    excel_grades: dict[str, float],
    grp_grades: list[GrpStudentGrade],
) -> AuditPreview:
    """Generate a full audit preview — never writes to GRP.

    Returns an ``AuditPreview`` with the diff, counts, and a ``blocked``
    flag when students in Excel are not found in GRP.
    """
    diff = compare_grades(excel_students, excel_grades, grp_grades)
    blocked = any(i.change_type == "not_found" for i in diff.items)
    changes = sum(
        1 for i in diff.items if i.change_type in ("new", "changed")
    )

    return AuditPreview(
        context=context,
        diff=diff,
        total_students=len(grp_grades),
        changes_count=changes,
        blocked=blocked,
    )
