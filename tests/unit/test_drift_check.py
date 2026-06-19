"""Unit tests for deployed-version drift detection."""

from __future__ import annotations

import httpx
import pytest

from voyager.core.drift_check import (
    check_drift,
    compare_release_versions,
    create_drift_alert_issue,
    drift_alert_body,
    drift_alert_title,
    fetch_healthz_version,
    fetch_latest_release_tag,
    parse_semver,
    run_drift_alert_once,
)

# ---- parse_semver -----------------------------------------------------------


class TestParseSemver:
    def test_standard_release_tag(self) -> None:
        assert parse_semver("v0.5.0") == (0, 5, 0, ())

    def test_without_v_prefix(self) -> None:
        assert parse_semver("1.2.3") == (1, 2, 3, ())

    def test_multi_digit(self) -> None:
        assert parse_semver("v10.200.3000") == (10, 200, 3000, ())

    def test_whitespace_stripped(self) -> None:
        assert parse_semver("  v0.5.0  ") == (0, 5, 0, ())

    def test_prerelease_not_matched(self) -> None:
        assert parse_semver("v0.5.0-rc1") is None

    def test_build_metadata_preserved_for_stable_release(self) -> None:
        assert parse_semver("v0.5.0+build42") == (0, 5, 0, ("build42",))
        assert parse_semver("v10.20.30+build.5") == (10, 20, 30, ("build", "5"))

    def test_prerelease_with_build_metadata_not_matched(self) -> None:
        assert parse_semver("v0.5.0-rc1+build42") is None

    def test_non_semver_returns_none(self) -> None:
        assert parse_semver("latest") is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_semver("") is None

    @pytest.mark.parametrize(
        ("tag", "expected"),
        [
            ("v0.4.0", (0, 4, 0, ())),
            ("v0.4.9", (0, 4, 9, ())),
            ("v0.5.0", (0, 5, 0, ())),
            ("v0.5.1", (0, 5, 1, ())),
            ("v1.0.0", (1, 0, 0, ())),
        ],
    )
    def test_comparison_order(
        self, tag: str, expected: tuple[int, int, int, tuple[str, ...]]
    ) -> None:
        parsed = parse_semver(tag)
        assert parsed == expected
        assert compare_release_versions(parsed, (9, 9, 9, ())) < 0
        assert compare_release_versions(parsed, (0, 0, 0, ())) > 0

    def test_build_metadata_is_release_tiebreaker(self) -> None:
        stable = parse_semver("0.6.0")
        build = parse_semver("v0.6.0+build.1")
        assert stable is not None
        assert build is not None
        assert compare_release_versions(stable, build) < 0
        assert compare_release_versions(build, stable) > 0


# ---- fetch_latest_release_tag -----------------------------------------------


class TestFetchLatestReleaseTag:
    async def test_returns_highest_stable_semver_tag(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=[
                    {"tag_name": "v0.6.1", "draft": False, "prerelease": False},
                    {"tag_name": "v0.7.0", "draft": False, "prerelease": False},
                    {"tag_name": "v0.8.0-rc.1", "draft": False, "prerelease": True},
                    {"tag_name": "v9.9.9", "draft": True, "prerelease": False},
                    {"tag_name": "not-a-version", "draft": False, "prerelease": False},
                ],
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            tag = await fetch_latest_release_tag(
                client, "iterwheel/voyager", github_token="ghp_test"
            )
        assert tag == "v0.7.0"

    async def test_returns_build_metadata_tiebreaker(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=[
                    {"tag_name": "v0.6.0", "draft": False, "prerelease": False},
                    {"tag_name": "v0.6.0+build.1", "draft": False, "prerelease": False},
                ],
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            tag = await fetch_latest_release_tag(
                client, "iterwheel/voyager", github_token="ghp_test"
            )
        assert tag == "v0.6.0+build.1"

    async def test_returns_none_on_http_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            tag = await fetch_latest_release_tag(
                client, "iterwheel/voyager", github_token="ghp_test"
            )
        assert tag is None


# ---- fetch_healthz_version --------------------------------------------------


class TestFetchHealthzVersion:
    async def test_returns_version(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"version": "0.4.0"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            version = await fetch_healthz_version(client, "http://localhost:8787")
        assert version == "0.4.0"

    async def test_returns_none_on_http_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(502)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            version = await fetch_healthz_version(client, "http://localhost:8787")
        assert version is None


# ---- check_drift ------------------------------------------------------------


def _make_mock_client(
    latest_tag: str, deployed_version: str, issues: list | None = None
) -> httpx.AsyncClient:
    """Return an AsyncClient pre-wired with mock responses."""
    import json as _json

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/releases" in url:
            return httpx.Response(
                200,
                json=[{"tag_name": latest_tag, "draft": False, "prerelease": False}],
            )
        if "/healthz" in url:
            return httpx.Response(200, json={"version": deployed_version})
        if "/issues" in url and request.method == "GET":
            return httpx.Response(200, json=issues or [])
        if "/issues" in url and request.method == "POST":
            body = _json.loads(request.content)
            return httpx.Response(201, json={"number": 42, "title": body.get("title", "")})
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class TestCheckDrift:
    async def test_deployed_behind_latest_returns_drifted(self) -> None:
        client = _make_mock_client(latest_tag="v0.5.0", deployed_version="0.4.0")
        result = await check_drift(
            "iterwheel/voyager",
            "http://localhost:8787",
            github_token="ghp_test",
            http_client=client,
        )
        assert result["drifted"] is True
        assert result["ok"] is False
        assert result["latest_tag"] == "v0.5.0"
        assert result["deployed_version"] == "0.4.0"
        assert "behind" in (result["summary"] or "")

    async def test_versions_equal_returns_no_drift(self) -> None:
        client = _make_mock_client(latest_tag="v0.5.0", deployed_version="0.5.0")
        result = await check_drift(
            "iterwheel/voyager",
            "http://localhost:8787",
            github_token="ghp_test",
            http_client=client,
        )
        assert result["drifted"] is False
        assert result["ok"] is True
        assert "matches" in (result["summary"] or "")

    async def test_build_metadata_newer_latest_returns_drifted(self) -> None:
        client = _make_mock_client(latest_tag="v0.6.0+build.1", deployed_version="0.6.0")
        result = await check_drift(
            "iterwheel/voyager",
            "http://localhost:8787",
            github_token="ghp_test",
            http_client=client,
        )
        assert result["drifted"] is True
        assert result["ok"] is False

    async def test_same_build_metadata_returns_no_drift(self) -> None:
        client = _make_mock_client(latest_tag="v0.6.0+build.1", deployed_version="0.6.0+build.1")
        result = await check_drift(
            "iterwheel/voyager",
            "http://localhost:8787",
            github_token="ghp_test",
            http_client=client,
        )
        assert result["drifted"] is False
        assert result["ok"] is True

    async def test_deployed_ahead_returns_no_drift(self) -> None:
        client = _make_mock_client(latest_tag="v0.4.0", deployed_version="0.5.0")
        result = await check_drift(
            "iterwheel/voyager",
            "http://localhost:8787",
            github_token="ghp_test",
            http_client=client,
        )
        assert result["drifted"] is False
        assert result["ok"] is True

    async def test_missing_tag_returns_not_ok(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if "/releases" in str(request.url):
                return httpx.Response(404)
            if "/healthz" in str(request.url):
                return httpx.Response(200, json={"version": "0.4.0"})
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await check_drift(
                "iterwheel/voyager",
                "http://localhost:8787",
                github_token="ghp_test",
                http_client=client,
            )
        assert result["ok"] is False
        assert result["latest_tag"] is None

    async def test_missing_healthz_returns_not_ok(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if "/releases" in str(request.url):
                return httpx.Response(
                    200,
                    json=[{"tag_name": "v0.5.0", "draft": False, "prerelease": False}],
                )
            if "/healthz" in str(request.url):
                return httpx.Response(502)
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await check_drift(
                "iterwheel/voyager",
                "http://localhost:8787",
                github_token="ghp_test",
                http_client=client,
            )
        assert result["ok"] is False
        assert result["deployed_version"] is None

    async def test_unparseable_tag_returns_not_ok(self) -> None:
        client = _make_mock_client(latest_tag="random-string", deployed_version="0.4.0")
        result = await check_drift(
            "iterwheel/voyager",
            "http://localhost:8787",
            github_token="ghp_test",
            http_client=client,
        )
        assert result["ok"] is False
        assert result["drifted"] is None

    async def test_drift_alert_creation(self) -> None:
        client = _make_mock_client(latest_tag="v0.5.0", deployed_version="0.4.0", issues=[])
        created = await create_drift_alert_issue(
            "iterwheel/voyager",
            github_token="ghp_test",
            deployed_version="0.4.0",
            latest_tag="v0.5.0",
            http_client=client,
        )
        assert created is not None
        assert created["number"] == 42

    async def test_drift_alert_skips_when_already_open(self) -> None:
        open_issues = [
            {
                "number": 7,
                "title": "[Drift Alert] Deployed version behind latest release v0.5.0",
                "state": "open",
            }
        ]
        client = _make_mock_client(
            latest_tag="v0.5.0", deployed_version="0.4.0", issues=open_issues
        )
        created = await create_drift_alert_issue(
            "iterwheel/voyager",
            github_token="ghp_test",
            deployed_version="0.4.0",
            latest_tag="v0.5.0",
            http_client=client,
        )
        assert created is None

    async def test_drift_alert_checks_later_issue_pages_before_creating(self) -> None:
        title = "[Drift Alert] Deployed version behind latest release v0.5.0"
        filler = [{"number": idx, "title": f"unrelated issue {idx}"} for idx in range(100)]
        post_attempted = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal post_attempted
            if request.method == "GET" and "/issues" in str(request.url):
                page = int(request.url.params.get("page", "1"))
                if page == 1:
                    return httpx.Response(200, json=filler)
                return httpx.Response(
                    200,
                    json=[{"number": 101, "title": title, "state": "open"}],
                )
            if request.method == "POST" and "/issues" in str(request.url):
                post_attempted = True
                return httpx.Response(201, json={"number": 102})
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            created = await create_drift_alert_issue(
                "iterwheel/voyager",
                github_token="ghp_test",
                deployed_version="0.4.0",
                latest_tag="v0.5.0",
                http_client=client,
            )

        assert created is None
        assert post_attempted is False

    async def test_scheduled_drift_check_creates_alert_for_older_deploy(self) -> None:
        client = _make_mock_client(latest_tag="v0.5.0", deployed_version="0.4.0", issues=[])
        result = await run_drift_alert_once(
            "iterwheel/voyager",
            "http://localhost:8787",
            github_token="ghp_test",
            http_client=client,
        )
        assert result["drifted"] is True
        assert result["alert_created"] is True
        assert result["alert_issue_number"] == 42

    async def test_scheduled_drift_check_skips_alert_when_versions_equal(self) -> None:
        client = _make_mock_client(latest_tag="v0.5.0", deployed_version="0.5.0")
        result = await run_drift_alert_once(
            "iterwheel/voyager",
            "http://localhost:8787",
            github_token="ghp_test",
            http_client=client,
        )
        assert result["drifted"] is False
        assert result["alert_created"] is False
        assert result["alert_issue_number"] is None


# ---- alert formatting -------------------------------------------------------


class TestDriftAlertFormatting:
    def test_title_includes_latest_tag(self) -> None:
        title = drift_alert_title("v0.5.0")
        assert "v0.5.0" in title
        assert "[Drift Alert]" in title

    def test_body_includes_both_versions(self) -> None:
        body = drift_alert_body("0.4.0", "v0.5.0")
        assert "0.4.0" in body
        assert "v0.5.0" in body
        assert "Wukong" in body
