from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from voyager.release_readiness import (
    evaluate_release_readiness,
    latest_release_tag,
    release_readiness_prs,
    render_result,
)


def test_current_changelog_covers_shippable_prs_since_latest_release() -> None:
    repo = Path(__file__).resolve().parents[1]
    _ensure_release_history_available_on_ci(repo)

    tag = latest_release_tag(repo=repo)
    result = evaluate_release_readiness(
        changelog_text=(repo / "CHANGELOG.md").read_text(encoding="utf-8"),
        prs_since_tag=release_readiness_prs(repo=repo, tag=tag),
        tag=tag,
    )

    if not result.ok:
        rendered = render_result(result)
        for line in rendered:
            print(line)
        pytest.fail("\n".join(rendered))


def _ensure_release_history_available_on_ci(repo: Path) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return

    fetch_args = ["git", "fetch", "--force", "--prune", "--tags"]
    if (repo / ".git" / "shallow").exists():
        fetch_args.append("--unshallow")
    fetch_args.append("origin")

    result = subprocess.run(
        fetch_args,
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr.strip() or "failed to fetch release history")
