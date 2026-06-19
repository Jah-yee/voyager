"""CLI entry point: ``vyg`` command."""

from __future__ import annotations

import typer
import uvicorn

app = typer.Typer(no_args_is_help=True)
bridge_app = typer.Typer(no_args_is_help=True)
app.add_typer(bridge_app, name="bridge")


@app.command("version")
def version() -> None:
    """Print Voyager version and build commit."""
    from voyager.build_info import BUILD_COMMIT, VERSION

    typer.echo(f"version: {VERSION}")
    typer.echo(f"build_commit: {BUILD_COMMIT}")


@bridge_app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host."),
    port: int = typer.Option(8787, "--port", help="Bind port."),
    log_level: str = typer.Option("info", "--log-level", help="Uvicorn log level."),
) -> None:
    """Start the bridge HTTP server via uvicorn."""
    uvicorn.run("voyager.server:app", host=host, port=port, log_level=log_level)


@bridge_app.command("check-drift")
def check_drift(
    bridge_url: str = typer.Argument(..., help="Bridge URL (e.g. http://localhost:8787)."),
    repo: str = typer.Option("iterwheel/voyager", "--repo", help="GitHub repository (owner/name)."),
    git_token: str = typer.Option(
        "", "--git-token", envvar="GITHUB_TOKEN", help="GitHub API token."
    ),
    create_issue: bool = typer.Option(
        False, "--create-issue", help="Create a drift alert GitHub issue."
    ),
) -> None:
    """Check for deployed-version drift between the latest release tag
    and the /healthz endpoint of a running bridge."""
    import asyncio

    from voyager.core.drift_check import (
        check_drift,
        create_drift_alert_issue,
    )

    async def _run() -> None:
        if not git_token:
            typer.echo("ERROR: --git-token or GITHUB_TOKEN env var is required")
            raise typer.Exit(code=1)

        result = await check_drift(
            repo=repo,
            bridge_url=bridge_url,
            github_token=git_token,
        )

        typer.echo(f"latest_tag:       {result['latest_tag']}")
        typer.echo(f"deployed_version: {result['deployed_version']}")
        typer.echo(f"drifted:          {result['drifted']}")
        typer.echo(f"summary:          {result['summary']}")

        if not result["ok"] and result["drifted"] and create_issue:
            created = await create_drift_alert_issue(
                repo=repo,
                github_token=git_token,
                deployed_version=result["deployed_version"],
                latest_tag=result["latest_tag"],
            )
            if created:
                typer.echo(f"Created alert issue #{created.get('number')}")
            else:
                typer.echo("Alert issue already exists or could not be created")

    asyncio.run(_run())


def main() -> None:
    """Entry point for the ``vyg`` console script."""
    app()


if __name__ == "__main__":
    main()
