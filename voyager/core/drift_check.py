"""Deployed-version drift alert — latest release tag vs Wukong /healthz."""

from __future__ import annotations

import logging
import re
from typing import Any, cast

import httpx

_log = logging.getLogger(__name__)

_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:\+([A-Za-z0-9.-]+))?$")
_GITHUB_API = "https://api.github.com"
_GITHUB_API_VERSION = "2022-11-28"
_RELEASES_PATH = "/repos/{repo}/releases"
_HEALTHZ_PATH = "/healthz"


def parse_semver(tag_or_version: str) -> tuple[int, int, int, tuple[str, ...]] | None:
    """Parse ``vX.Y.Z`` or ``X.Y.Z`` into a comparable release key, or ``None``."""
    m = _SEMVER_RE.match(tag_or_version.strip())
    if m:
        build = tuple(m.group(4).split(".")) if m.group(4) else ()
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)), build)
    return None


def compare_release_versions(
    left: tuple[int, int, int, tuple[str, ...]],
    right: tuple[int, int, int, tuple[str, ...]],
) -> int:
    """Compare release versions using build metadata as Voyager's release tiebreaker."""
    left_core = left[:3]
    right_core = right[:3]
    if left_core != right_core:
        return -1 if left_core < right_core else 1
    return _compare_build_tiebreaker(left[3], right[3])


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
    left_is_numeric = left.isdigit()
    right_is_numeric = right.isdigit()
    if left_is_numeric and right_is_numeric:
        left_int = int(left)
        right_int = int(right)
        if left_int == right_int:
            return 0
        return -1 if left_int < right_int else 1
    if left_is_numeric != right_is_numeric:
        return -1 if left_is_numeric else 1
    if left == right:
        return 0
    return -1 if left < right else 1


async def fetch_latest_release_tag(
    client: httpx.AsyncClient, repo: str, *, github_token: str
) -> str | None:
    """Fetch the highest stable SemVer release tag."""
    path = _RELEASES_PATH.format(repo=repo)
    headers = _github_headers(github_token)
    try:
        best_tag: str | None = None
        best_version: tuple[int, int, int, tuple[str, ...]] | None = None
        per_page = 100
        page = 1
        while True:
            resp = await client.get(
                f"{_GITHUB_API}{path}",
                params={"per_page": per_page, "page": page},
                headers=headers,
            )
            resp.raise_for_status()
            releases = resp.json()
            for release in releases:
                if release.get("draft") or release.get("prerelease"):
                    continue
                tag = release.get("tag_name")
                if not isinstance(tag, str):
                    continue
                parsed = parse_semver(tag)
                if parsed is None:
                    continue
                if best_version is None or compare_release_versions(best_version, parsed) < 0:
                    best_tag = tag
                    best_version = parsed
            if len(releases) < per_page:
                return best_tag
            page += 1
    except httpx.HTTPError:
        _log.warning("No releases found for %s", repo)
        return None


async def fetch_healthz_version(client: httpx.AsyncClient, bridge_url: str) -> str | None:
    """Fetch the version field from the bridge's /healthz endpoint."""
    url = f"{bridge_url.rstrip('/')}{_HEALTHZ_PATH}"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return cast("str | None", resp.json().get("version"))
    except httpx.HTTPError:
        _log.warning("Cannot reach /healthz at %s", url)
        return None


async def check_drift(
    repo: str,
    bridge_url: str,
    *,
    github_token: str,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Compare latest release tag to deployed /healthz version.

    Returns a dict with keys:

    - **ok** (``bool``): ``True`` when versions are in sync or determinable.
    - **drifted** (``bool | None``): ``True`` when deployed < latest,
      ``None`` if versions could not be compared.
    - **latest_tag** (``str | None``)
    - **deployed_version** (``str | None``)
    - **summary** (``str | None``): human-readable explanation.
    """
    own_client = http_client is None
    client: httpx.AsyncClient
    if own_client:
        client = httpx.AsyncClient(timeout=15)
    else:
        assert http_client is not None
        client = http_client

    try:
        latest_tag, deployed_version = await _fetch_both(
            client, repo, bridge_url, github_token=github_token
        )

        result: dict[str, Any] = {
            "ok": True,
            "drifted": None,
            "latest_tag": latest_tag,
            "deployed_version": deployed_version,
            "summary": None,
        }

        if not latest_tag or not deployed_version:
            result["ok"] = False
            result["summary"] = "Could not determine versions from GitHub release or /healthz"
            return result

        latest_sv = parse_semver(latest_tag)
        deployed_sv = parse_semver(deployed_version)

        if latest_sv is None or deployed_sv is None:
            result["ok"] = False
            result["summary"] = (
                f"Could not parse semver: latest={latest_tag!r} deployed={deployed_version!r}"
            )
            return result

        if compare_release_versions(deployed_sv, latest_sv) < 0:
            result["drifted"] = True
            result["ok"] = False
            result["summary"] = (
                f"Deployed version {deployed_version} is behind latest release {latest_tag}"
            )
        else:
            result["drifted"] = False
            result["summary"] = (
                f"Deployed version {deployed_version} matches latest release {latest_tag}"
            )

        return result
    finally:
        if own_client:
            await client.aclose()


async def run_drift_alert_once(
    repo: str,
    bridge_url: str,
    *,
    github_token: str,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Run one scheduled drift check and create an alert issue on drift."""
    result = await check_drift(
        repo,
        bridge_url,
        github_token=github_token,
        http_client=http_client,
    )
    result["alert_created"] = False
    result["alert_issue_number"] = None

    if result["drifted"] is not True:
        return result

    latest_tag = result["latest_tag"]
    deployed_version = result["deployed_version"]
    if not isinstance(latest_tag, str) or not isinstance(deployed_version, str):
        return result

    created = await create_drift_alert_issue(
        repo,
        github_token=github_token,
        deployed_version=deployed_version,
        latest_tag=latest_tag,
        http_client=http_client,
    )
    if created:
        result["alert_created"] = True
        result["alert_issue_number"] = created.get("number")
    return result


async def _fetch_both(
    client: httpx.AsyncClient,
    repo: str,
    bridge_url: str,
    *,
    github_token: str,
) -> tuple[str | None, str | None]:
    """Fetch latest tag and healthz version in parallel."""
    import asyncio

    tag_task = fetch_latest_release_tag(client, repo, github_token=github_token)
    healthz_task = fetch_healthz_version(client, bridge_url)
    results = await asyncio.gather(tag_task, healthz_task, return_exceptions=True)
    tag: str | None = results[0] if not isinstance(results[0], BaseException) else None
    ver: str | None = results[1] if not isinstance(results[1], BaseException) else None
    return tag, ver


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": _GITHUB_API_VERSION,
    }


def drift_alert_title(latest_tag: str) -> str:
    """Return the GitHub issue title for a drift alert."""
    return f"[Drift Alert] Deployed version behind latest release {latest_tag}"


def drift_alert_body(deployed_version: str, latest_tag: str) -> str:
    """Return the GitHub issue body for a drift alert."""
    return (
        f"A deployed-version drift has been detected.\n\n"
        f"- **Latest release**: {latest_tag}\n"
        f"- **Deployed version**: {deployed_version}\n\n"
        f"Action required: redeploy Wukong to match the latest release."
    )


async def create_drift_alert_issue(
    repo: str,
    *,
    github_token: str,
    deployed_version: str,
    latest_tag: str,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """Create a drift alert issue on the repository, or return ``None`` if one is
    already open with the same title."""
    own_client = http_client is None
    client: httpx.AsyncClient
    if own_client:
        client = httpx.AsyncClient(timeout=15)
    else:
        assert http_client is not None
        client = http_client

    try:
        title = drift_alert_title(latest_tag)
        body = drift_alert_body(deployed_version, latest_tag)

        headers = _github_headers(github_token)
        owner, name = repo.split("/", 1)

        if await _open_issue_with_title_exists(client, owner, name, title, headers=headers):
            return None

        resp = await client.post(
            f"{_GITHUB_API}/repos/{owner}/{name}/issues",
            headers=headers,
            json={"title": title, "body": body},
        )
        resp.raise_for_status()
        created = cast("dict[str, Any]", resp.json())
        _log.info("Created drift alert issue #%s", created.get("number"))

        return created
    except httpx.HTTPError:
        _log.exception("Failed to create drift alert issue")
        return None
    finally:
        if own_client:
            await client.aclose()


async def _open_issue_with_title_exists(
    client: httpx.AsyncClient,
    owner: str,
    name: str,
    title: str,
    *,
    headers: dict[str, str],
) -> bool:
    per_page = 100
    page = 1
    while True:
        resp = await client.get(
            f"{_GITHUB_API}/repos/{owner}/{name}/issues",
            params={"state": "open", "per_page": per_page, "page": page},
            headers=headers,
        )
        resp.raise_for_status()
        issues = resp.json()
        for existing in issues:
            if existing.get("title") == title:
                _log.info("Drift alert issue already open: #%s", existing.get("number"))
                return True
        if len(issues) < per_page:
            return False
        page += 1
