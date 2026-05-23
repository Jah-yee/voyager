#!/usr/bin/env bash
# Build a deployable Voyager wheel with the current git SHA baked into
# voyager/_build_info.py. The SHA is read at runtime by voyager.build_info
# and reported via /healthz so operators can verify which artifact is live.
#
# Usage:
#   bash scripts/build_wheel.sh
#
# Refuses to build a dirty tree by default. Override:
#   VOYAGER_BUILD_ALLOW_DIRTY=1 bash scripts/build_wheel.sh

set -euo pipefail

command -v git >/dev/null 2>&1 || { echo "ERROR: git not found in PATH" >&2; exit 127; }
command -v uv  >/dev/null 2>&1 || { echo "ERROR: uv not found in PATH"  >&2; exit 127; }

commit=$(git rev-parse HEAD)

if [ -n "$(git status --porcelain)" ] && [ -z "${VOYAGER_BUILD_ALLOW_DIRTY:-}" ]; then
  echo "ERROR: dirty working tree; commit or stash changes, or export VOYAGER_BUILD_ALLOW_DIRTY=1 to override" >&2
  exit 1
fi

trap 'rm -f voyager/_build_info.py' EXIT INT TERM HUP

printf 'BUILD_COMMIT = "%s"\n' "$commit" > voyager/_build_info.py

uv build

wheel=$(ls -t dist/iterwheel_voyager-*.whl | head -1)
if [ -z "$wheel" ] || [ ! -f "$wheel" ]; then
  echo "ERROR: no wheel produced under dist/" >&2
  exit 2
fi

if ! unzip -l "$wheel" | grep -q 'voyager/_build_info.py'; then
  echo "ERROR: _build_info.py missing from wheel ($wheel); check [tool.hatch.build] artifacts in pyproject.toml" >&2
  exit 2
fi

echo "built: $wheel"
echo "commit: $commit"
