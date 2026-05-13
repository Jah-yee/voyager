"""Unit tests for voyager.bots.clearance.severity.

Covers the SWM-1102 §B row 1 demotion rule and all pass-through paths.
Red phase: these tests fail with ImportError until the production module exists.
"""

from __future__ import annotations

import pytest

from voyager.bots.clearance.models import Severity
from voyager.bots.clearance.severity import (
    SeverityDecision,
    evaluate,
)

# ---------------------------------------------------------------------------
# Scenario matrix: demote path
# ---------------------------------------------------------------------------

_DEMOTE_CASES = [
    # (codex_severity, base_branch, expected_effective)
    (Severity.P1, "main", Severity.P2),
    (Severity.P2, "develop", Severity.P3),
    (Severity.P1, "release/v2", Severity.P2),
]


@pytest.mark.parametrize(("codex_sev", "base_branch", "expected_eff"), _DEMOTE_CASES)
def test_demote_path(codex_sev: Severity, base_branch: str, expected_eff: Severity) -> None:
    """P1/P2 + required_check_coupling + unprotected branch → demote one step."""
    decision = evaluate(
        codex_severity=codex_sev,
        finding_kind="required_check_coupling",
        branch_protected=False,
        base_branch=base_branch,
    )
    assert decision.effective_severity == expected_eff
    assert decision.codex_severity == codex_sev
    assert decision.reason is not None
    assert base_branch in decision.reason
    assert "no branch protection" in decision.reason


# ---------------------------------------------------------------------------
# Scenario matrix: pass-through path
# ---------------------------------------------------------------------------

_PASSTHROUGH_CASES = [
    # (codex_severity, finding_kind, branch_protected, base_branch)
    (Severity.P1, "required_check_coupling", True, "main"),  # protected → no demotion
    (Severity.P1, None, False, "main"),  # no finding_kind
    (Severity.P1, "something_else", False, "main"),  # unrelated kind
    (Severity.P3, "required_check_coupling", False, "main"),  # P3 cannot demote further
    (Severity.P2, "required_check_coupling", True, "main"),  # protected → no demotion
]


@pytest.mark.parametrize(
    ("codex_sev", "finding_kind", "branch_protected", "base_branch"),
    _PASSTHROUGH_CASES,
)
def test_passthrough_path(
    codex_sev: Severity,
    finding_kind: str | None,
    branch_protected: bool,
    base_branch: str,
) -> None:
    """No demotion conditions met → effective_severity == codex_severity, reason is None."""
    decision = evaluate(
        codex_severity=codex_sev,
        finding_kind=finding_kind,
        branch_protected=branch_protected,
        base_branch=base_branch,
    )
    assert decision.effective_severity == codex_sev
    assert decision.codex_severity == codex_sev
    assert decision.reason is None


# ---------------------------------------------------------------------------
# Identity / invariant properties
# ---------------------------------------------------------------------------


def test_codex_severity_always_equals_input() -> None:
    """Returned codex_severity always equals input (audit invariant)."""
    for sev in Severity:
        decision = evaluate(
            codex_severity=sev,
            finding_kind="required_check_coupling",
            branch_protected=False,
            base_branch="main",
        )
        assert decision.codex_severity is sev


def test_reason_not_none_when_effective_differs() -> None:
    """When effective_severity != codex_severity, reason must be set."""
    decision = evaluate(
        codex_severity=Severity.P1,
        finding_kind="required_check_coupling",
        branch_protected=False,
        base_branch="main",
    )
    assert decision.effective_severity != decision.codex_severity
    assert decision.reason is not None


def test_reason_none_when_effective_equals_codex() -> None:
    """When effective_severity == codex_severity, reason must be None."""
    decision = evaluate(
        codex_severity=Severity.P1,
        finding_kind=None,
        branch_protected=False,
        base_branch="main",
    )
    assert decision.effective_severity == decision.codex_severity
    assert decision.reason is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_base_branch_demotes_without_crash() -> None:
    """Empty base_branch on demote path: still demotes; reason does not contain 'None'."""
    decision = evaluate(
        codex_severity=Severity.P1,
        finding_kind="required_check_coupling",
        branch_protected=False,
        base_branch="",
    )
    assert decision.effective_severity == Severity.P2
    assert decision.reason is not None
    assert "None" not in decision.reason


def test_empty_string_finding_kind_is_passthrough() -> None:
    """finding_kind='' is not 'required_check_coupling' → no demotion."""
    decision = evaluate(
        codex_severity=Severity.P1,
        finding_kind="",
        branch_protected=False,
        base_branch="main",
    )
    assert decision.effective_severity == Severity.P1
    assert decision.reason is None


# ---------------------------------------------------------------------------
# SeverityDecision structural check
# ---------------------------------------------------------------------------


def test_severity_decision_is_frozen_dataclass() -> None:
    """SeverityDecision instances are immutable (frozen=True)."""
    decision = evaluate(
        codex_severity=Severity.P2,
        finding_kind=None,
        branch_protected=True,
        base_branch="main",
    )
    assert isinstance(decision, SeverityDecision)
    with pytest.raises((AttributeError, TypeError)):
        decision.reason = "mutate"  # type: ignore[misc]
