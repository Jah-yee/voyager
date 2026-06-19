from __future__ import annotations

from voyager.core.review_identity import extract_codex_title_id, extract_known_limitation_rule_id


def test_codex_title_id_skips_standalone_severity_marker() -> None:
    body = "**P2**\nAvoid stale cache writes\n\nDetails changed."

    assert extract_codex_title_id(body) == "codex-title:avoid stale cache writes"


def test_known_limitation_rule_id_combines_kind_with_next_line_title() -> None:
    body = "**P2**\nRequired check paths-ignore build\n\nDetails changed."

    assert (
        extract_known_limitation_rule_id(body)
        == "required_check_coupling:codex-title:required check paths-ignore build"
    )


def test_codex_title_id_preserves_angle_bracket_code() -> None:
    body = "[P1] Reject <script> injection"

    assert extract_codex_title_id(body) == "codex-title:reject <script> injection"
