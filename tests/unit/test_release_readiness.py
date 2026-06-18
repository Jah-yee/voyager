from __future__ import annotations

import json
from pathlib import Path

import pytest

from voyager import release_readiness
from voyager.release_readiness import (
    MergedPullRequest,
    evaluate_release_readiness,
    is_shippable_pr,
    latest_release_tag,
    parse_merge_prs,
    render_result,
    unreleased_section_has_content,
    versioned_release_section_has_content,
)


def _changelog(unreleased: str) -> str:
    return f"""# Changelog

## [Unreleased]
{unreleased}

## [0.5.0] - 2026-06-17

- Prior release.
"""


def _release_changelog(*, unreleased: str, pending_release: str) -> str:
    return _release_changelog_for_version(
        version="0.6.0",
        unreleased=unreleased,
        pending_release=pending_release,
    )


def _release_changelog_for_version(
    *,
    version: str,
    unreleased: str,
    pending_release: str,
) -> str:
    return f"""# Changelog

## [Unreleased]
{unreleased}

## [{version}] - 2026-06-19
{pending_release}

## [0.5.0] - 2026-06-17

- Prior release.
"""


def _task_pr(number: int = 162) -> MergedPullRequest:
    return MergedPullRequest(
        number=number,
        title="[Task]: Release-readiness check",
        branch="iterwheel/162-release-readiness-check",
        sha="a" * 40,
    )


def test_empty_unreleased_with_shippable_prs_fails_with_pr_list() -> None:
    result = evaluate_release_readiness(
        changelog_text=_changelog(""),
        prs_since_tag=[_task_pr(162), _task_pr(163)],
        tag="v0.5.0",
    )

    assert result.ok is False
    assert [pr.number for pr in result.missing_prs] == [162, 163]
    rendered = "\n".join(render_result(result))
    assert "::error title=Empty CHANGELOG [Unreleased]::" in rendered
    assert "#162 [Task]: Release-readiness check" in rendered
    assert "#163 [Task]: Release-readiness check" in rendered


def test_populated_unreleased_with_shippable_prs_passes() -> None:
    result = evaluate_release_readiness(
        changelog_text=_changelog("\n### Added\n\n- Release-readiness check.\n"),
        prs_since_tag=[_task_pr()],
        tag="v0.5.0",
    )

    assert result.ok is True
    assert result.missing_prs == ()


def test_empty_unreleased_with_pending_versioned_release_notes_passes() -> None:
    result = evaluate_release_readiness(
        changelog_text=_release_changelog(
            unreleased="",
            pending_release="\n### Added\n\n- Release-readiness check.\n",
        ),
        prs_since_tag=[_task_pr()],
        tag="v0.5.0",
    )

    assert result.ok is True
    assert result.unreleased_has_content is False
    assert result.versioned_release_has_content is True
    assert "Versioned release changelog section has content" in "\n".join(render_result(result))


def test_empty_unreleased_with_empty_pending_versioned_section_still_fails() -> None:
    result = evaluate_release_readiness(
        changelog_text=_release_changelog(unreleased="", pending_release="\n<!-- reserved -->\n"),
        prs_since_tag=[_task_pr()],
        tag="v0.5.0",
    )

    assert result.ok is False
    assert result.missing_prs == (_task_pr(),)


def test_unreleased_comment_only_counts_as_empty() -> None:
    assert unreleased_section_has_content(_changelog("\n<!-- reserved -->\n")) is False


def test_multiline_html_comment_only_counts_as_empty() -> None:
    placeholder = "\n<!--\nreserved for release notes\n-->\n"

    assert unreleased_section_has_content(_changelog(placeholder)) is False
    assert (
        versioned_release_section_has_content(
            _release_changelog(unreleased="", pending_release=placeholder),
            "v0.5.0",
        )
        is False
    )


def test_structural_changelog_heading_only_counts_as_empty() -> None:
    assert unreleased_section_has_content(_changelog("\n### Added\n")) is False
    assert (
        versioned_release_section_has_content(
            _release_changelog(unreleased="", pending_release="\n### Added\n"),
            "v0.5.0",
        )
        is False
    )


def test_versioned_release_notes_stop_at_latest_tag() -> None:
    assert (
        versioned_release_section_has_content(
            _release_changelog(
                unreleased="",
                pending_release="\n### Added\n\n- Release-readiness check.\n",
            ),
            "v0.5.0",
        )
        is True
    )
    assert versioned_release_section_has_content(_changelog(""), "v0.5.0") is False


def test_versioned_release_notes_accept_combined_prerelease_build_heading() -> None:
    assert (
        versioned_release_section_has_content(
            _release_changelog_for_version(
                version="0.6.0-rc.1+build.5",
                unreleased="",
                pending_release="\n### Added\n\n- Release-readiness check.\n",
            ),
            "v0.5.0",
        )
        is True
    )


def test_latest_release_tag_uses_semver_precedence_and_build_tiebreaker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_git(args: list[str], *, repo: Path) -> str:
        assert args == ["tag", "--list", "v[0-9]*"]
        assert repo == Path(".")
        return "\n".join(
            [
                "v0.6.0-rc.1",
                "v0.6.0",
                "v0.6.0+build.1",
                "v0.6.0-rc.2",
                "v0.5.10",
                "not-a-version",
            ]
        )

    monkeypatch.setattr(release_readiness, "_git", fake_git)

    assert latest_release_tag(repo=Path(".")) == "v0.6.0+build.1"


def test_release_readiness_prs_includes_current_pull_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "number": 175,
                    "title": "[Task]: Release-readiness check",
                    "head": {"ref": "162-release-readiness", "sha": "d" * 40},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

    def fake_merged_prs_since_tag(*, repo: Path, tag: str | None) -> list[MergedPullRequest]:
        assert repo == Path(".")
        assert tag == "v0.5.0"
        return []

    monkeypatch.setattr(release_readiness, "merged_prs_since_tag", fake_merged_prs_since_tag)

    assert release_readiness.release_readiness_prs(repo=Path("."), tag="v0.5.0") == [
        MergedPullRequest(
            number=175,
            title="[Task]: Release-readiness check",
            branch="162-release-readiness",
            sha="d" * 40,
        )
    ]


def test_parse_merge_prs_uses_body_first_line_as_title() -> None:
    log = (
        "a" * 40
        + "\x1fMerge pull request #173 from iterwheel/161-maturity-level-gate-field\x1f"
        + "[Task]: Maturity-level gate field (Closes #161)\n\nextra body"
        + "\x1e"
        + "b" * 40
        + "\x1fMerge remote-tracking branch 'origin/main' into feature\x1f\x1e"
    )

    prs = parse_merge_prs(log)

    assert len(prs) == 1
    assert prs[0].number == 173
    assert prs[0].title == "[Task]: Maturity-level gate field (Closes #161)"
    assert prs[0].branch == "iterwheel/161-maturity-level-gate-field"


def test_shippable_filter_excludes_release_and_docs_prs() -> None:
    assert is_shippable_pr(_task_pr()) is True
    assert (
        is_shippable_pr(
            MergedPullRequest(
                number=195,
                title="feat!: remove legacy API",
                branch="iterwheel/breaking-feature",
                sha="f" * 40,
            )
        )
        is True
    )
    assert (
        is_shippable_pr(
            MergedPullRequest(
                number=196,
                title="fix(api)!: rename response field",
                branch="iterwheel/breaking-fix",
                sha="1" * 40,
            )
        )
        is True
    )
    assert (
        is_shippable_pr(
            MergedPullRequest(
                number=197,
                title="chore!: drop old runtime",
                branch="iterwheel/breaking-chore",
                sha="2" * 40,
            )
        )
        is True
    )
    assert (
        is_shippable_pr(
            MergedPullRequest(
                number=198,
                title="[Bug]: Fix stale PR scanner",
                branch="iterwheel/166-stale-pr-triage",
                sha="d" * 40,
            )
        )
        is True
    )
    assert (
        is_shippable_pr(
            MergedPullRequest(
                number=199,
                title="[Feature]: Draft changelog automatically",
                branch="iterwheel/163-changelog-draft",
                sha="e" * 40,
            )
        )
        is True
    )
    assert (
        is_shippable_pr(
            MergedPullRequest(
                number=200,
                title="release: v0.5.1",
                branch="iterwheel/release/v0.5.1",
                sha="b" * 40,
            )
        )
        is False
    )
    assert (
        is_shippable_pr(
            MergedPullRequest(
                number=201,
                title="docs: update runbook",
                branch="iterwheel/docs/update-runbook",
                sha="c" * 40,
            )
        )
        is False
    )
