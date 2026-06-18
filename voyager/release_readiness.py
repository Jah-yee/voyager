"""Release-readiness checks for changelog drift."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil

# Bandit: subprocess is used only for fixed-argv local git commands.
import subprocess  # nosec B404
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cmp_to_key
from pathlib import Path

_SEMVER_TAG_RE = re.compile(
    r"^v(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)
_VERSION_HEADING_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
_MERGE_PR_RE = re.compile(r"^Merge pull request #(?P<number>\d+) from (?P<branch>\S+)")
_CHANGELOG_HEADING_RE = re.compile(r"^## \[(?P<name>[^\]]+)\]")
_SKIP_TITLE_RE = re.compile(r"^(chore|ci|docs?|refactor|style|tests?)(?:\(.+\))?:", re.I)
_BREAKING_TITLE_RE = re.compile(r"^[a-z]+(?:\([^)]+\))?!:", re.I)
_SHIP_TITLE_RE = re.compile(r"^(feat|fix|perf|build\(deps\)|security)(?:\(.+\))?!?:", re.I)
_SHIP_BLUEPRINT_TITLE_RE = re.compile(r"^\[(task|bug|feature)\]:", re.I)
_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"


@dataclass(frozen=True)
class MergedPullRequest:
    number: int
    title: str
    branch: str
    sha: str

    @property
    def display(self) -> str:
        title = self.title or self.branch
        return f"#{self.number} {title}"


@dataclass(frozen=True)
class ReleaseReadinessResult:
    ok: bool
    tag: str | None
    shippable_prs: tuple[MergedPullRequest, ...]
    unreleased_has_content: bool
    versioned_release_has_content: bool = False

    @property
    def missing_prs(self) -> tuple[MergedPullRequest, ...]:
        if self.ok:
            return ()
        return self.shippable_prs


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...]
    build: tuple[str, ...]


def unreleased_section_has_content(changelog_text: str) -> bool:
    """Return True when CHANGELOG.md has non-comment content under [Unreleased]."""
    return _section_has_content(changelog_text, "unreleased")


def versioned_release_section_has_content(changelog_text: str, tag: str | None) -> bool:
    """Return True when a pending versioned release section has changelog notes."""
    if not tag:
        return False
    current_version = tag.removeprefix("v")
    in_versioned_section = False
    section_has_content = False
    in_html_comment = False
    for line in changelog_text.splitlines():
        heading = _CHANGELOG_HEADING_RE.match(line.strip())
        if heading:
            if in_versioned_section and section_has_content:
                return True
            name = heading.group("name").strip()
            if name == current_version:
                return False
            in_versioned_section = bool(_VERSION_HEADING_RE.fullmatch(name))
            section_has_content = False
            in_html_comment = False
            continue
        has_content, in_html_comment = _changelog_line_content_state(
            line,
            in_html_comment=in_html_comment if in_versioned_section else False,
        )
        if in_versioned_section and has_content:
            section_has_content = True
    return in_versioned_section and section_has_content


def _section_has_content(changelog_text: str, section_name: str) -> bool:
    in_section = False
    in_html_comment = False
    for line in changelog_text.splitlines():
        heading = _CHANGELOG_HEADING_RE.match(line.strip())
        if heading:
            if in_section:
                return False
            in_section = heading.group("name").strip().lower() == section_name
            in_html_comment = False
            continue
        if not in_section:
            continue
        has_content, in_html_comment = _changelog_line_content_state(
            line,
            in_html_comment=in_html_comment,
        )
        if has_content:
            return True
    return False


def _changelog_line_content_state(line: str, *, in_html_comment: bool) -> tuple[bool, bool]:
    stripped = line.strip()
    if in_html_comment:
        return False, "-->" not in stripped
    if not stripped or stripped.startswith("#"):
        return False, False
    if stripped.startswith("<!--"):
        return False, "-->" not in stripped
    return True, False


def parse_merge_prs(log_output: str) -> list[MergedPullRequest]:
    """Parse `git log` records into GitHub merge PR metadata."""
    prs: list[MergedPullRequest] = []
    for raw_record in log_output.split(_RECORD_SEP):
        record = raw_record.strip("\n")
        if not record:
            continue
        fields = record.split(_FIELD_SEP, 2)
        if len(fields) != 3:
            continue
        sha, subject, body = fields
        match = _MERGE_PR_RE.match(subject.strip())
        if not match:
            continue
        title = _first_non_empty_line(body)
        prs.append(
            MergedPullRequest(
                number=int(match.group("number")),
                title=title,
                branch=match.group("branch"),
                sha=sha.strip(),
            )
        )
    return prs


def shippable_prs(prs: Sequence[MergedPullRequest]) -> list[MergedPullRequest]:
    """Filter merge PRs to changes that should normally appear in the changelog."""
    return [pr for pr in prs if is_shippable_pr(pr)]


def is_shippable_pr(pr: MergedPullRequest) -> bool:
    title = pr.title.strip()
    branch = pr.branch.lower()
    title_lower = title.lower()
    if "dependabot/" in branch:
        return True
    if branch.startswith(("iterwheel/release/", "release/")) or title_lower.startswith("release:"):
        return False
    if _BREAKING_TITLE_RE.match(title):
        return True
    if _SKIP_TITLE_RE.match(title):
        return False
    if _SHIP_TITLE_RE.match(title):
        return True
    return bool(_SHIP_BLUEPRINT_TITLE_RE.match(title_lower))


def evaluate_release_readiness(
    *,
    changelog_text: str,
    prs_since_tag: Sequence[MergedPullRequest],
    tag: str | None,
) -> ReleaseReadinessResult:
    shippable = tuple(shippable_prs(prs_since_tag))
    has_content = unreleased_section_has_content(changelog_text)
    has_versioned_release_notes = versioned_release_section_has_content(changelog_text, tag)
    return ReleaseReadinessResult(
        ok=has_content or has_versioned_release_notes or not shippable,
        tag=tag,
        shippable_prs=shippable,
        unreleased_has_content=has_content,
        versioned_release_has_content=has_versioned_release_notes,
    )


def latest_release_tag(*, repo: Path) -> str | None:
    output = _git(
        ["tag", "--list", "v[0-9]*"],
        repo=repo,
    )
    candidates: list[tuple[str, SemVer]] = []
    for line in output.splitlines():
        tag = line.strip()
        version = _parse_semver_tag(tag)
        if version is not None:
            candidates.append((tag, version))
    if not candidates:
        return None
    return max(candidates, key=cmp_to_key(_compare_tag_versions))[0]


def release_readiness_prs(*, repo: Path, tag: str | None) -> list[MergedPullRequest]:
    prs = merged_prs_since_tag(repo=repo, tag=tag)
    current_pr = github_event_pull_request()
    if current_pr is not None and all(pr.number != current_pr.number for pr in prs):
        prs.append(current_pr)
    return prs


def github_event_pull_request(
    *,
    event_name: str | None = None,
    event_path: Path | None = None,
) -> MergedPullRequest | None:
    resolved_event_name = event_name or os.environ.get("GITHUB_EVENT_NAME")
    if resolved_event_name not in {"pull_request", "pull_request_target"}:
        return None

    resolved_event_path = event_path or _github_event_path_from_env()
    if resolved_event_path is None:
        raise RuntimeError(
            "GITHUB_EVENT_PATH is required for pull_request release-readiness checks"
        )

    payload = json.loads(resolved_event_path.read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request") or {}
    head = pull_request.get("head") or {}
    try:
        number = int(pull_request["number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("pull_request event payload is missing a numeric PR number") from exc
    title = str(pull_request.get("title") or "").strip()
    if not title:
        raise RuntimeError("pull_request event payload is missing a PR title")
    branch = str(head.get("ref") or head.get("label") or "").strip()
    sha = str(head.get("sha") or "").strip()
    return MergedPullRequest(number=number, title=title, branch=branch, sha=sha)


def merged_prs_since_tag(*, repo: Path, tag: str | None) -> list[MergedPullRequest]:
    range_arg = f"{tag}..HEAD" if tag else "HEAD"
    output = _git(
        ["log", "--merges", "--format=%H%x1f%s%x1f%b%x1e", range_arg],
        repo=repo,
    )
    return parse_merge_prs(output)


def render_result(result: ReleaseReadinessResult) -> list[str]:
    tag = result.tag or "<none>"
    if result.ok:
        if result.unreleased_has_content:
            return ["CHANGELOG [Unreleased] has content; release-readiness check passed."]
        if result.versioned_release_has_content:
            return [
                "Versioned release changelog section has content; release-readiness check passed."
            ]
        return [f"No shippable merged PRs found since {tag}; release-readiness check passed."]

    missing = "; ".join(pr.display for pr in result.missing_prs)
    return [
        _github_annotation(
            "error",
            "Empty CHANGELOG [Unreleased]",
            f"Shippable PRs merged since {tag}, but CHANGELOG.md [Unreleased] is empty: {missing}",
        ),
        f"Shippable PRs since {tag} need changelog coverage:",
        *[f"- {pr.display}" for pr in result.missing_prs],
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    changelog_path = args.changelog
    if not changelog_path.is_absolute():
        changelog_path = repo / changelog_path

    tag = latest_release_tag(repo=repo)
    prs = release_readiness_prs(repo=repo, tag=tag)
    result = evaluate_release_readiness(
        changelog_text=changelog_path.read_text(encoding="utf-8"),
        prs_since_tag=prs,
        tag=tag,
    )
    for line in render_result(result):
        print(line)
    return 0 if result.ok else 1


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _git(args: Sequence[str], *, repo: Path) -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise RuntimeError("git executable not found on PATH")
    result = subprocess.run(
        [git_executable, *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )  # nosec B603
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def _parse_semver_tag(tag: str) -> SemVer | None:
    match = _SEMVER_TAG_RE.fullmatch(tag)
    if not match:
        return None
    prerelease = match.group("prerelease")
    return SemVer(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease=tuple(prerelease.split(".")) if prerelease else (),
        build=tuple((match.group("build") or "").split(".")) if match.group("build") else (),
    )


def _compare_tag_versions(left: tuple[str, SemVer], right: tuple[str, SemVer]) -> int:
    return _compare_semver(left[1], right[1])


def _compare_semver(left: SemVer, right: SemVer) -> int:
    core = (left.major, left.minor, left.patch)
    other_core = (right.major, right.minor, right.patch)
    if core != other_core:
        return -1 if core < other_core else 1
    if not left.prerelease and right.prerelease:
        return 1
    if left.prerelease and not right.prerelease:
        return -1
    for left_part, right_part in zip(left.prerelease, right.prerelease, strict=False):
        compared = _compare_semver_identifier(left_part, right_part)
        if compared:
            return compared
    if len(left.prerelease) == len(right.prerelease):
        return _compare_build_tiebreaker(left.build, right.build)
    return -1 if len(left.prerelease) < len(right.prerelease) else 1


def _compare_build_tiebreaker(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    if not left and not right:
        return 0
    if not left:
        return -1
    if not right:
        return 1
    for left_part, right_part in zip(left, right, strict=False):
        compared = _compare_semver_identifier(left_part, right_part)
        if compared:
            return compared
    if len(left) == len(right):
        return 0
    return -1 if len(left) < len(right) else 1


def _compare_semver_identifier(left: str, right: str) -> int:
    if left == right:
        return 0
    left_numeric = left.isdigit()
    right_numeric = right.isdigit()
    if left_numeric and right_numeric:
        left_value = int(left)
        right_value = int(right)
        if left_value != right_value:
            return -1 if left_value < right_value else 1
        return 0
    if left_numeric != right_numeric:
        return -1 if left_numeric else 1
    return -1 if left < right else 1


def _github_event_path_from_env() -> Path | None:
    raw_path = os.environ.get("GITHUB_EVENT_PATH")
    if not raw_path:
        return None
    return Path(raw_path)


def _github_annotation(level: str, title: str, message: str) -> str:
    return f"::{level} title={_escape_annotation(title)}::{_escape_annotation(message)}"


def _escape_annotation(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
