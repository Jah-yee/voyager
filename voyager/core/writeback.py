from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .github_app import GitHubAppClient


def dry_run_enabled() -> bool:
    return os.environ.get("DRY_RUN", "true").lower() != "false"


async def apply_route_writeback(
    client: GitHubAppClient,
    route: dict[str, Any],
    *,
    repository: str | None,
) -> dict[str, Any]:
    if not repository:
        return {"applied": False, "reason": "missing repository"}

    app_slug = route["agent"]
    validation = route["validation"]
    issue_number = validation.get("issue_number")
    if not issue_number:
        return {"applied": False, "reason": "missing issue number"}

    writeback = route.get("writeback") or {}
    labels = writeback.get("labels") or {}
    reactions = writeback.get("reactions") or {}
    add_labels: list[str] = list(labels.get("add") or [])
    remove_labels: list[str] = list(labels.get("remove") or [])
    add_reactions: list[str] = list(reactions.get("add") or [])
    remove_reactions: list[str] = list(reactions.get("remove") or [])
    planned: dict[str, Any] = {
        "comment": bool(writeback.get("comment_body")),
        "add_labels": add_labels,
        "remove_labels": remove_labels,
        "add_reactions": add_reactions,
        "remove_reactions": remove_reactions,
    }

    if dry_run_enabled():
        return {"applied": False, "dry_run": True, "planned": planned}

    for label in remove_labels:
        await client.remove_label(app_slug, repository, int(issue_number), label)
    if add_labels:
        await client.add_labels(app_slug, repository, int(issue_number), add_labels)

    for reaction in remove_reactions:
        await client.remove_issue_reaction(app_slug, repository, int(issue_number), reaction)
    for reaction in add_reactions:
        await client.add_issue_reaction(app_slug, repository, int(issue_number), reaction)

    comment = None
    if writeback.get("comment_body"):
        if writeback.get("comment_mode") == "append":
            comment = await client.create_issue_comment(
                app_slug,
                repository,
                int(issue_number),
                body=writeback["comment_body"],
            )
        else:
            comment = await client.upsert_issue_comment(
                app_slug,
                repository,
                int(issue_number),
                marker=writeback["comment_marker"],
                body=writeback["comment_body"],
            )

    return {
        "applied": True,
        "dry_run": False,
        "planned": planned,
        "comment_url": (comment or {}).get("html_url"),
    }
