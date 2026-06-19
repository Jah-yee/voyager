"""CI-failing sweep — find open PRs with red CI and flag them.

This module is not webhook-driven; it runs as a scheduled daily task
dispatched from ``voyager.server`` alongside the deployed-version drift
check and stale-PR triage.  There is no route dispatch, no writeback
envelope — the server calls ``run_ci_failing_sweep`` directly within the
background loop.

Each open PR whose latest commit has a ``failure`` check-run conclusion
gets a ``ci-failing`` label and a reminder comment.  At most one comment
per failing run (identified by the check-run's ``id``) is created — the
comment body embeds a marker ``<!-- voyager:ci-failing-run-{run_id} -->``
so re-runs of the same check produce at most one comment.

PRs whose latest check runs are all green (or absent) have the
``ci-failing`` label removed if present.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from voyager.core.github_app import GitHubAppClient

_log = logging.getLogger(__name__)

CI_FAILING_AGENT_SLUG = "iterwheel-assembly"
CI_FAILING_LABEL = "ci-failing"
CI_FAILING_LABEL_COLOR = "dc3545"
CI_FAILING_LABEL_DESCRIPTION = "Latest CI run is failing on this pull request."
CI_FAILING_COMMENT_MARKER_PREFIX = "<!-- voyager:ci-failing-run-"
_SEARCH_PAGE_SIZE = 100

# Check conclusion values that count as "red"
_FAILING_CONCLUSIONS = frozenset({"failure", "timed_out", "cancelled", "action_required"})


def _ci_failing_marker(run_id: int) -> str:
    """Return the HTML-comment marker for a specific check-run id."""
    return f"{CI_FAILING_COMMENT_MARKER_PREFIX}{run_id} -->"


async def _find_open_prs(
    client: GitHubAppClient,
    app_slug: str,
    repo: str,
) -> list[dict[str, Any]]:
    """Return all open PRs for *repo* via the GitHub Search Issues API."""
    owner, name = repo.split("/", 1)
    prs: list[dict[str, Any]] = []
    page = 1
    while True:
        path = (
            f"/search/issues"
            f"?q=repo%3A{owner}%2F{name}+type%3Apr+state%3Aopen"
            f"&per_page={_SEARCH_PAGE_SIZE}&sort=updated&order=asc&page={page}"
        )
        data = await client.request(app_slug, "GET", path, repository=repo)
        items = list((data or {}).get("items") or [])
        prs.extend(items)
        if len(items) < _SEARCH_PAGE_SIZE:
            return prs
        page += 1


async def _has_ci_failing_label(pr: dict[str, Any]) -> bool:
    """Return ``True`` when the PR already carries the ``ci-failing`` label."""
    labels = pr.get("labels") or []
    return any(
        (isinstance(label, dict) and label.get("name") == CI_FAILING_LABEL)
        or label == CI_FAILING_LABEL
        for label in labels
    )


async def _existing_ci_failing_comment(
    client: GitHubAppClient,
    app_slug: str,
    repo: str,
    issue_number: int,
    run_id: int,
) -> bool:
    """Return ``True`` when a bot comment with the given run-id marker already exists."""
    comments = await client.issue_comments(app_slug, repo, issue_number)
    marker = _ci_failing_marker(run_id)
    bot_login = f"{app_slug}[bot]"
    for comment in comments:
        user = comment.get("user") or {}
        if user.get("login") != bot_login:
            continue
        body = str(comment.get("body") or "")
        if marker in body:
            return True
    return False


async def run_ci_failing_sweep(
    client: GitHubAppClient,
    app_slug: str,
    repo: str,
) -> dict[str, Any]:
    """Run one CI-failing sweep cycle: find open PRs, check latest CI, flag failures.

    Returns a summary dict with counts and lists of affected PR numbers.
    """
    prs = await _find_open_prs(client, app_slug, repo)
    flagged: list[int] = []
    cleared: list[int] = []
    skipped_no_checks: list[int] = []
    already_failing: list[int] = []
    label_ensured = False

    for pr in prs:
        pr_number = pr.get("number")
        if not isinstance(pr_number, int):
            continue

        # Fetch the full PR object to get the head SHA
        try:
            full_pr = await client.pull_request(app_slug, repo, pr_number)
        except Exception:
            _log.exception("Failed to fetch PR #%d details", pr_number)
            continue

        head = full_pr.get("head") or {}
        head_sha = head.get("sha")
        if not isinstance(head_sha, str) or not head_sha:
            skipped_no_checks.append(pr_number)
            continue

        # Fetch check runs for the head commit
        try:
            check_runs = await client.commit_check_runs(app_slug, repo, head_sha)
        except Exception:
            _log.exception("Failed to fetch check runs for PR #%d commit %s", pr_number, head_sha)
            continue

        if not check_runs:
            skipped_no_checks.append(pr_number)
            continue

        # Find failing check runs
        failing_runs = [run for run in check_runs if run.get("conclusion") in _FAILING_CONCLUSIONS]

        has_ci_failing_label = await _has_ci_failing_label(pr)

        if failing_runs:
            # At least one check run is failing — flag the PR
            if not label_ensured:
                try:
                    await client.ensure_label(
                        app_slug,
                        repo,
                        CI_FAILING_LABEL,
                        color=CI_FAILING_LABEL_COLOR,
                        description=CI_FAILING_LABEL_DESCRIPTION,
                    )
                    label_ensured = True
                except Exception:
                    _log.exception("Failed to ensure ci-failing label exists")
                    continue

            if not has_ci_failing_label:
                try:
                    await client.add_labels(app_slug, repo, pr_number, [CI_FAILING_LABEL])
                except Exception:
                    _log.exception("Failed to add ci-failing label to PR #%d", pr_number)
                    continue
            else:
                already_failing.append(pr_number)

            # Comment on the first failing run only (idempotent per run-id)
            first_failing = failing_runs[0]
            run_id = first_failing.get("id")
            run_name = str(first_failing.get("name", "unknown"))
            run_url = str(first_failing.get("html_url", ""))
            if isinstance(run_id, int):
                already_commented = await _existing_ci_failing_comment(
                    client,
                    app_slug,
                    repo,
                    pr_number,
                    run_id,
                )
                if not already_commented:
                    try:
                        marker = _ci_failing_marker(run_id)
                        body = (
                            f"{marker}\n\n"
                            f"🔴 CI check **{run_name}** is failing on this pull request.\n\n"
                            f"See [{run_name}]({run_url}) for details.\n\n"
                            f"_Automated CI sweep — Iterwheel Bridge_"
                        )
                        await client.create_issue_comment(
                            app_slug,
                            repo,
                            pr_number,
                            body=body,
                        )
                    except Exception:
                        _log.exception(
                            "Failed to add ci-failing comment to PR #%d for run %d",
                            pr_number,
                            run_id,
                        )

            flagged.append(pr_number)

        elif has_ci_failing_label:
            # PR was red before but now green — remove the label
            try:
                await client.remove_label(app_slug, repo, pr_number, CI_FAILING_LABEL)
                cleared.append(pr_number)
            except Exception:
                _log.exception("Failed to remove ci-failing label from PR #%d", pr_number)

        else:
            skipped_no_checks.append(pr_number)

    return {
        "checked": len(prs),
        "flagged": flagged,
        "cleared": cleared,
        "already_failing": already_failing,
        "skipped_no_checks": skipped_no_checks,
    }
