"""Extract severity and finding-kind from Codex review thread comments.

Pure extraction logic (no I/O, no state mutation). Maps raw GitHub comment
bodies to Severity enum members and optional finding-kind strings.
"""

from __future__ import annotations

from voyager.bots.clearance.models import Severity
from voyager.core.review_identity import extract_required_check_finding_kind


def extract_severity_and_kind(
    comments: list[dict] | None,
) -> tuple[Severity, str | None]:
    """Extract (codex_severity, finding_kind) from Codex review thread comments.

    Severity rule: scan first comment body for any of these markers:
      "![P1 Badge]", "![P2 Badge]", "![P3 Badge]"
      "|P1|", "|P2|", "|P3|"
      "**P1**", "**P2**", "**P3**"
    Returns Severity.P1/P2/P3 on first match; Severity.P3 if no match.

    Finding-kind rule (case-insensitive): if body contains ALL of "required",
    ("check" OR "status"), and "paths-ignore" → "required_check_coupling".
    Otherwise None.

    Empty comments / None comments → (Severity.P3, None).
    """
    if not comments:
        return Severity.P3, None

    body = comments[0].get("body") or ""

    severity = _extract_severity(body)
    kind = _extract_finding_kind(body)

    return severity, kind


def _extract_severity(body: str) -> Severity:
    """Extract severity from badge markers in comment body.

    Checks for literal case markers (in priority order P1 → P2 → P3 so a
    P1-marked thread containing an incidental P2 mention still scores P1):
      "![PN Badge]"  image-badge markdown
      "|PN|"         table-cell delimiter
      "**PN**"       bold
      "[PN]"         bracket prefix (e.g. "[P1] SQL injection ...")  ← Codex r1 P1

    Returns Severity.P1/P2/P3 on first match; defaults to Severity.P3.

    Codex PR-#12 P1 finding: previously the bracketed `[P1]` / `[P2]` / `[P3]`
    format (a common Codex title style) fell through to the P3 default, which
    under β rule 4 silently unblocks PRs that should have stayed blocked.
    Adding `[PN]` to the marker set closes the silent-downgrade path.
    """
    for sev in ("P1", "P2", "P3"):
        if (
            f"![{sev} Badge]" in body
            or f"|{sev}|" in body
            or f"**{sev}**" in body
            or f"[{sev}]" in body
        ):
            return Severity(sev)
    return Severity.P3


def _extract_finding_kind(body: str) -> str | None:
    """Extract finding_kind from comment body.

    Returns "required_check_coupling" if body contains ALL of:
      - "required" (case-insensitive)
      - "check" OR "status" (case-insensitive)
      - "paths-ignore" (case-insensitive)

    Otherwise returns None.
    """
    return extract_required_check_finding_kind(body)
