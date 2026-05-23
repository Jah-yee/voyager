"""Wheel-integration smoke test (CHG-1820 Surface 14).

Test contract — asserts two invariants about the wheel built by
``scripts/build_wheel.sh``:

1. The wheel contains ``voyager/_build_info.py`` (regression gate for
   hatchling's gitignore-exclusion behavior).
2. That file's ``BUILD_COMMIT`` equals the current ``git rev-parse HEAD``
   (regression gate for the build script's SHA-injection step).

Marked ``slow`` (deselected by default in the fast unit loop) and skipped
when ``uv`` is unavailable.

Protocol: snapshot ``dist/`` before; build via ``bash scripts/build_wheel.sh``;
set-diff to find the new wheel; verify with ``zipfile.ZipFile``; cleanup the
new wheel(s) so ``dist/`` returns to its pre-test state.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.skipif(not shutil.which("uv"), reason="uv required for wheel build")


@pytest.mark.slow
def test_built_wheel_contains_build_info_and_reports_commit() -> None:
    dist_dir = PROJECT_ROOT / "dist"
    before: set[str] = set()
    if dist_dir.exists():
        before = {p.name for p in dist_dir.iterdir() if p.is_file()}

    build_script = PROJECT_ROOT / "scripts" / "build_wheel.sh"
    subprocess.run(
        ["bash", str(build_script)],
        cwd=PROJECT_ROOT,
        check=True,
    )

    after = {p.name for p in dist_dir.iterdir() if p.is_file()}
    new_files = after - before
    new_wheels = [n for n in new_files if n.endswith(".whl")]
    assert len(new_wheels) == 1, f"expected exactly one new wheel, got {new_wheels}"

    new_wheel_path = dist_dir / new_wheels[0]
    try:
        current_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        with zipfile.ZipFile(new_wheel_path) as zf:
            names = zf.namelist()
            assert "voyager/_build_info.py" in names, (
                f"_build_info.py missing from wheel; namelist: {names}"
            )
            content = zf.read("voyager/_build_info.py")
            expected = f'BUILD_COMMIT = "{current_sha}"\n'.encode()
            assert content == expected, (
                f"build_info content mismatch:\n  got: {content!r}\n  want: {expected!r}"
            )
    finally:
        for name in new_files:
            (dist_dir / name).unlink(missing_ok=True)
