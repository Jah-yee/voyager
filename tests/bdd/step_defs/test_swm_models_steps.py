"""Step definitions for SWM models BDD scenarios."""

from __future__ import annotations

from datetime import UTC

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/swm_models.feature")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts():
    from datetime import datetime

    return datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC)


def _base_thread_dict(*, extra: dict | None = None) -> dict:
    d = {
        "id": "PRRT_abc",
        "comment_id": 1001,
        "path": "app.py",
        "line": 10,
        "codex_severity": "P2",
        "effective_severity": "P2",
        "verdict": "OPEN",
    }
    if extra:
        d.update(extra)
    return d


def _base_poll_record(*, head_sha: str = "abc1234", codex_open: int = 1):
    from voyager.bots.clearance.models import CIConclusion, PollRecord, Status

    return PollRecord(
        ts=_ts(),
        repo="owner/repo",
        pr=49,
        head_sha=head_sha,
        status=Status.PENDING,
        ci={"ubuntu": CIConclusion.SUCCESS},
        codex_open=codex_open,
    )


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------


@given("the SWM Status enum", target_fixture="status_enum")
def get_status_enum():
    from voyager.bots.clearance.models import Status

    return Status


@then(parsers.parse("the Status enum has members {members}"))
def status_has_members(status_enum, members: str) -> None:
    expected = [m.strip() for m in members.split(",")]
    values = {m.value for m in status_enum}
    for e in expected:
        assert e in values, f"{e!r} not in Status enum values: {values}"


# ---------------------------------------------------------------------------
# Verdict enum
# ---------------------------------------------------------------------------


@given("the SWM Verdict enum", target_fixture="verdict_enum")
def get_verdict_enum():
    from voyager.bots.clearance.models import Verdict

    return Verdict


@then(parsers.parse("the Verdict enum has members {members}"))
def verdict_has_members(verdict_enum, members: str) -> None:
    expected = [m.strip() for m in members.split(",")]
    values = {m.value for m in verdict_enum}
    for e in expected:
        assert e in values, f"{e!r} not in Verdict enum values: {values}"


# ---------------------------------------------------------------------------
# Severity enum
# ---------------------------------------------------------------------------


@given("the SWM Severity enum", target_fixture="severity_enum")
def get_severity_enum():
    from voyager.bots.clearance.models import Severity

    return Severity


@then(parsers.parse("the Severity enum has members {members}"))
def severity_has_members(severity_enum, members: str) -> None:
    expected = [m.strip() for m in members.split(",")]
    values = {m.value for m in severity_enum}
    for e in expected:
        assert e in values, f"{e!r} not in Severity enum values: {values}"


# ---------------------------------------------------------------------------
# CIConclusion enum
# ---------------------------------------------------------------------------


@given("the SWM CIConclusion enum", target_fixture="ci_enum")
def get_ci_enum():
    from voyager.bots.clearance.models import CIConclusion

    return CIConclusion


@then(parsers.parse("the CIConclusion enum has members {members}"))
def ci_has_members(ci_enum, members: str) -> None:
    expected = [m.strip() for m in members.split(",")]
    values = {m.value for m in ci_enum}
    for e in expected:
        assert e in values, f"{e!r} not in CIConclusion enum values: {values}"


# ---------------------------------------------------------------------------
# Thread model
# ---------------------------------------------------------------------------


@given(
    parsers.parse('a valid Thread dict with id "{tid}" and severity "{sev}"'),
    target_fixture="thread_dict",
)
def valid_thread_dict(tid: str, sev: str) -> dict:
    return _base_thread_dict()


@given("a Thread dict with an extra unknown field", target_fixture="thread_dict")
def thread_dict_extra_field() -> dict:
    return _base_thread_dict(extra={"unknown_future_field": "some_value"})


@when("the Thread dict is validated", target_fixture="thread_model")
def validate_thread_dict(thread_dict: dict):
    from voyager.bots.clearance.models import Thread

    return Thread.model_validate(thread_dict)


@then(parsers.parse('the Thread model is valid with verdict "{verdict}"'))
def thread_model_valid(thread_model, verdict: str) -> None:
    assert thread_model.verdict.value == verdict


# ---------------------------------------------------------------------------
# PollRecord state_key
# ---------------------------------------------------------------------------


@given("two identical PollRecord instances", target_fixture="two_polls")
def two_identical_polls() -> tuple:
    a = _base_poll_record()
    b = _base_poll_record()
    return a, b


@given("two PollRecord instances differing only in head_sha", target_fixture="two_polls")
def polls_differing_head_sha() -> tuple:
    a = _base_poll_record(head_sha="aaa1234")
    b = _base_poll_record(head_sha="bbb5678")
    return a, b


@given("two PollRecord instances differing only in codex_open count", target_fixture="two_polls")
def polls_differing_codex_open() -> tuple:
    a = _base_poll_record(codex_open=0)
    b = _base_poll_record(codex_open=1)
    return a, b


@when("their state_keys are computed", target_fixture="state_keys")
def compute_state_keys(two_polls: tuple) -> tuple:
    a, b = two_polls
    return a.state_key(), b.state_key()


@then("the state_keys are equal")
def state_keys_equal(state_keys: tuple) -> None:
    a, b = state_keys
    assert a == b


@then("the state_keys are not equal")
def state_keys_not_equal(state_keys: tuple) -> None:
    a, b = state_keys
    assert a != b


# ---------------------------------------------------------------------------
# PollRecord JSON round-trip
# ---------------------------------------------------------------------------


@given("a PollRecord with a thread and CI data", target_fixture="poll_record")
def poll_record_with_thread():
    from voyager.bots.clearance.models import (
        CIConclusion,
        PollRecord,
        Severity,
        Status,
        Thread,
        Verdict,
    )

    thread = Thread(
        id="PRRT_t1",
        comment_id=42,
        path="foo.py",
        codex_severity=Severity.P1,
        effective_severity=Severity.P2,
        verdict=Verdict.OPEN,
    )
    return PollRecord(
        ts=_ts(),
        repo="owner/repo",
        pr=7,
        head_sha="abc1234",
        status=Status.PENDING,
        ci={"ubuntu": CIConclusion.SUCCESS, "macos": CIConclusion.IN_PROGRESS},
        codex_open=1,
        threads=[thread],
    )


@when("the PollRecord is serialized and deserialized", target_fixture="roundtripped_poll")
def serialize_deserialize_poll(poll_record):
    from voyager.bots.clearance.models import PollRecord

    return PollRecord.model_validate_json(poll_record.model_dump_json())


@then("the deserialized PollRecord equals the original")
def roundtripped_poll_equals(roundtripped_poll, poll_record) -> None:
    assert roundtripped_poll == poll_record


# ---------------------------------------------------------------------------
# ThreadSnapshot JSON round-trip
# ---------------------------------------------------------------------------


@given("a ThreadSnapshot with evidence", target_fixture="thread_snapshot")
def thread_snapshot_with_evidence():
    from voyager.bots.clearance.models import (
        Evidence,
        GitHubThreadState,
        Severity,
        ThreadSnapshot,
        Verdict,
    )

    return ThreadSnapshot(
        thread_id="PRRT_snap1",
        repo="owner/repo",
        pr=49,
        first_seen=_ts(),
        last_polled=_ts(),
        codex_comment_id=1001,
        path="src/main.py",
        codex_severity=Severity.P2,
        effective_severity=Severity.P3,
        verdict=Verdict.RESOLVED,
        evidence=Evidence(
            thread_state="C",
            code_changed=True,
            code_change_commit="abc12345",
        ),
        github_state=GitHubThreadState(isResolved=True, resolvedBy="frankyxhl"),
    )


@when("the ThreadSnapshot is serialized and deserialized", target_fixture="roundtripped_snapshot")
def serialize_deserialize_snapshot(thread_snapshot):
    from voyager.bots.clearance.models import ThreadSnapshot

    return ThreadSnapshot.model_validate_json(thread_snapshot.model_dump_json())


@then("the deserialized ThreadSnapshot equals the original")
def roundtripped_snapshot_equals(roundtripped_snapshot, thread_snapshot) -> None:
    assert roundtripped_snapshot == thread_snapshot


# ---------------------------------------------------------------------------
# LedgerEntry
# ---------------------------------------------------------------------------


@given("a LedgerEntry JSON with extra legacy fields", target_fixture="ledger_json")
def ledger_entry_json_with_extras() -> str:
    return (
        '{"ts":"2026-05-08T00:57:42Z","repo":"owner/repo","pr":7,"head_sha":"abc",'
        '"action":"submit_review_approve","actor":"frankyxhl",'
        '"authorized_by":"maintainer","reason":"CI green","boxes_flipped":["A12"]}'
    )


@when("the LedgerEntry JSON is deserialized", target_fixture="ledger_entry")
def deserialize_ledger(ledger_json: str):
    from voyager.bots.clearance.models import LedgerEntry

    return LedgerEntry.model_validate_json(ledger_json)


@then(parsers.parse('the LedgerEntry action is "{action}"'))
def ledger_action(ledger_entry, action: str) -> None:
    assert ledger_entry.action.value == action


@then("the extra field is preserved")
def ledger_extra_field(ledger_entry) -> None:
    assert getattr(ledger_entry, "boxes_flipped", None) == ["A12"]


# ---------------------------------------------------------------------------
# BoxMiss
# ---------------------------------------------------------------------------


@given(
    parsers.parse('a BoxMiss with repo "{repo}" and reason "{reason}"'), target_fixture="box_miss"
)
def box_miss_no_rule_id(repo: str, reason: str):
    from voyager.bots.clearance.models import BoxMiss

    return BoxMiss(ts=_ts(), repo=repo, pr=1, head_sha="abc", box_text="box", reason=reason)


@given(
    parsers.parse('a BoxMiss with repo "{repo}" and rule_id "{rule_id}"'), target_fixture="box_miss"
)
def box_miss_with_rule_id(repo: str, rule_id: str):
    from voyager.bots.clearance.models import BoxMiss

    return BoxMiss(
        ts=_ts(), repo=repo, pr=1, head_sha="abc", box_text="box", reason="r", rule_id=rule_id
    )


@when("the BoxMiss is validated", target_fixture="validated_box_miss")
def validate_box_miss(box_miss):
    return box_miss


@then("the BoxMiss rule_id is None")
def box_miss_rule_id_none(validated_box_miss) -> None:
    assert validated_box_miss.rule_id is None


@then(parsers.parse('the BoxMiss rule_id is "{rule_id}"'))
def box_miss_rule_id(validated_box_miss, rule_id: str) -> None:
    assert validated_box_miss.rule_id == rule_id
