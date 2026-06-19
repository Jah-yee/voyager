from __future__ import annotations

import asyncio

import pytest

import voyager.server as server


@pytest.fixture(autouse=True)
async def clean_drift_alert_task(monkeypatch: pytest.MonkeyPatch):
    await server._stop_deployed_version_drift_schedule()
    monkeypatch.setattr(server, "_drift_alert_task", None)
    yield
    await server._stop_deployed_version_drift_schedule()


async def test_deployed_version_drift_schedule_stays_off_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BRIDGE_DRIFT_ALERT_ENABLED", raising=False)

    await server._start_deployed_version_drift_schedule()

    assert server._drift_alert_task is None


async def test_deployed_version_drift_schedule_starts_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_loop() -> None:
        await asyncio.Event().wait()

    monkeypatch.setenv("BRIDGE_DRIFT_ALERT_ENABLED", "true")
    monkeypatch.setattr(server, "_deployed_version_drift_loop", fake_loop)

    await server._start_deployed_version_drift_schedule()

    task = server._drift_alert_task
    assert task is not None
    assert not task.done()

    await server._stop_deployed_version_drift_schedule()

    assert server._drift_alert_task is None
