from __future__ import annotations

from datetime import UTC, datetime

import pytest

from voyager.governance.audit_log import (
    ReviewFixAuditLog,
    ReviewFixAuditLogError,
    ReviewFixAuditRecord,
)


def _record(round_number: int, verdict: str = "fixed") -> ReviewFixAuditRecord:
    return ReviewFixAuditRecord(
        round=round_number,
        ts=datetime(2026, 6, 20, 1, round_number, tzinfo=UTC),
        commit=f"deadbeef{round_number}",
        finding_id=f"codex-title:finding-{round_number}",
        category="codex-review",
        verdict=verdict,
        tests=("pytest tests/unit/test_governance_audit_log.py",),
    )


def test_append_then_read_yields_typed_records_in_order(tmp_path) -> None:
    path = tmp_path / "review-fix.jsonl"
    log = ReviewFixAuditLog(path)

    log.append(_record(1, "fixed"))
    log.append(_record(2, "accepted"))

    records = log.read_all()

    assert records == [_record(1, "fixed"), _record(2, "accepted")]


def test_log_persists_across_writer_instances(tmp_path) -> None:
    path = tmp_path / "review-fix.jsonl"

    ReviewFixAuditLog(path).append(_record(1))
    ReviewFixAuditLog(path).append(_record(2))

    assert ReviewFixAuditLog(path).read_all() == [_record(1), _record(2)]
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_malformed_line_is_surfaced_as_error(tmp_path) -> None:
    path = tmp_path / "review-fix.jsonl"
    ReviewFixAuditLog(path).append(_record(1))
    with path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")

    with pytest.raises(ReviewFixAuditLogError, match="line 2"):
        ReviewFixAuditLog(path).read_all()
