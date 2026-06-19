from __future__ import annotations

import re

_CODEX_TITLE_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_CODEX_TITLE_SUB_TAG_RE = re.compile(r"</?sub\b[^>]*>", re.IGNORECASE)
_CODEX_TITLE_SEVERITY_PREFIX_RE = re.compile(r"^(?:\[?P[123]\]?)(?:[\s:-]+|$)", re.IGNORECASE)


def extract_required_check_finding_kind(body: str) -> str | None:
    """Return the stable finding kind for required-check paths-ignore findings."""
    body_lower = body.lower()
    if (
        "required" in body_lower
        and ("check" in body_lower or "status" in body_lower)
        and "paths-ignore" in body_lower
    ):
        return "required_check_coupling"
    return None


def extract_codex_title_id(body: str) -> str | None:
    """Return a production-available Codex finding title identity."""
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = _CODEX_TITLE_MARKDOWN_IMAGE_RE.sub(" ", line)
        line = _CODEX_TITLE_SUB_TAG_RE.sub(" ", line)
        line = line.replace("**", " ").replace("__", " ")
        title = " ".join(line.split())
        title = _CODEX_TITLE_SEVERITY_PREFIX_RE.sub("", title).strip()
        if title:
            return f"codex-title:{title.casefold()}"
    return None


def extract_known_limitation_rule_id(body: str) -> str | None:
    """Return the preferred known-limitation identity available from a review body."""
    finding_kind = extract_required_check_finding_kind(body)
    title_id = extract_codex_title_id(body)
    if finding_kind and title_id:
        return f"{finding_kind}:{title_id}"
    return finding_kind or title_id
