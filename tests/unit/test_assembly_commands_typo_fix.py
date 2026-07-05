"""Unit tests for VOY-1817 Surface 13 fix: reject unknown flags (e.g. --dry_run typo).

The original parser silently ignored unknown flags, so ``/assembly --dry_run``
would parse as a plain ``/assembly`` and perform real GitHub mutations.
After the fix, unknown flags cause the parser to return None.
"""

from __future__ import annotations

import pytest

from voyager.bots.assembly.commands import parse_assembly_command


class TestTypoFlagRejection:
    """VOY-1817 Surface 13: typo flags must be rejected, not silently accepted."""

    @pytest.mark.parametrize(
        "body",
        [
            # The primary reported typo: underscore instead of hyphen
            "/assembly --dry_run",
            "/assembly --dry_run --some-other-flag",
            "/implement --dry_run",
            # Resume typo
            "/assembly --resume_",
            "/assembly --resume_ --dry-run",
            # allow-missing-stack typo
            "/assembly --allow_missing_stack",
            # Case-insensitive variants
            "/assembly --DRY_RUN",
            "/Assembly --Dry_Run",
            # With extra whitespace
            "/assembly  --dry_run",
            # Multiple unknown flags
            "/assembly --dry_run --allow_missing_stack",
        ],
    )
    def test_typo_flags_are_rejected(self, body: str) -> None:
        """Typo variants (underscore instead of hyphen) must return None.

        This is the core security property: a typo in a safety flag must
        NOT silently trigger a real mutation.
        """
        assert parse_assembly_command(body) is None, (
            f"Parser unexpectedly accepted typo flag in: {body!r}"
        )

    @pytest.mark.parametrize(
        "body",
        [
            # Legitimate flags must still be accepted
            "/assembly --dry-run",
            "/assembly --allow-missing-stack",
            "/assembly --resume",
            "/assembly --dry-run --allow-missing-stack",
            "/implement --dry-run --resume",
            "/assembly --dry-run --resume --allow-missing-stack",
            # With CRLF (legitimate flags still work)
            "/assembly --dry-run\r\n",
            "/assembly --resume\r\n",
        ],
    )
    def test_known_flags_still_accepted(self, body: str) -> None:
        """Legitimate flags (with hyphens) must continue to work."""
        cmd = parse_assembly_command(body)
        assert cmd is not None, f"Parser rejected legitimate flags in: {body!r}"

    def test_unknown_flag_alone_rejects(self) -> None:
        """Single unknown flag (not a typo, just unknown) also rejects."""
        assert parse_assembly_command("/assembly --completely-unknown") is None

    def test_mixed_known_and_unknown_rejects(self) -> None:
        """When unknown flags are present, the entire command rejects."""
        cmd = parse_assembly_command("/assembly --dry-run --completely-unknown")
        assert cmd is None

    def test_plain_command_still_works(self) -> None:
        """Plain /assembly without any flags must still be accepted."""
        cmd = parse_assembly_command("/assembly")
        assert cmd is not None
        assert cmd.dry_run is False
        assert cmd.allow_missing_stack is False
        assert cmd.resume is False
