"""Extract hunk(s) of a unified diff that touch a given (path, line) anchor.

This is the LLM investigator's input substrate per SWM-1101 §3 — false-addresses
verdicts (worst-class error: silently auto-resolving an unfixed thread) trace back
to bad excerpts fed to the investigator. This module is the single place where
the raw PR diff is sliced into the context window the investigator sees.

When ``line is None`` (GraphQL returns null for ``isOutdated=true`` threads —
anchor invalidated), all hunks for the path are returned so the investigator has
full per-file change context rather than an empty string.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class _Hunk:
    new_start: int
    new_len: int
    body_lines: list[str] = field(default_factory=list)  # body_lines[0] is the @@ header


_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_TRUNCATION_MARKER = "\n...[truncated]..."


def _parse_file_block(block_lines: list[str]) -> tuple[list[str], list[_Hunk]]:
    """Return (file_header_lines, hunks) parsed from a single per-file diff block."""
    file_header: list[str] = []
    hunks: list[_Hunk] = []
    current_hunk_lines: list[str] | None = None
    current_new_start = 0
    current_new_len = 0

    for line in block_lines:
        m = _HUNK_HEADER_RE.match(line)
        if m:
            if current_hunk_lines is not None:
                hunks.append(
                    _Hunk(
                        new_start=current_new_start,
                        new_len=current_new_len,
                        body_lines=current_hunk_lines,
                    )
                )
            current_new_start = int(m.group(1))
            current_new_len = int(m.group(2)) if m.group(2) is not None else 1
            current_hunk_lines = [line]
        elif current_hunk_lines is not None:
            current_hunk_lines.append(line)
        else:
            file_header.append(line)

    if current_hunk_lines is not None:
        hunks.append(
            _Hunk(
                new_start=current_new_start,
                new_len=current_new_len,
                body_lines=current_hunk_lines,
            )
        )

    return file_header, hunks


def _hunk_contains_line(hunk: _Hunk, line: int) -> bool:
    return hunk.new_start <= line < hunk.new_start + hunk.new_len


def _assemble(file_header: list[str], hunks: list[_Hunk]) -> str:
    parts = list(file_header)
    for hunk in hunks:
        parts.extend(hunk.body_lines)
    return "\n".join(parts)


def extract_anchor_excerpt(
    diff_text: str,
    *,
    path: str,
    line: int | None,
    max_chars: int = 20000,
) -> str:
    """Return the diff hunks of `diff_text` that touch the (path, line) anchor.

    Parameters:
        diff_text: raw unified diff text exactly as GitHub serves via
            ``application/vnd.github.v3.diff`` (see ``GitHubAppClient.pull_request_diff``).
            Empty string is treated as "no diff" and the function returns "".
        path: file path the Codex review comment anchored to. Matched against
            the `b/PATH` (new) side of the `diff --git a/PATH b/PATH` header
            since GitHub's review-thread `path` reflects the current head.
        line: line number on the new file side that the comment anchored to.
            When None (anchor invalidated by isOutdated=true GraphQL response),
            returns all hunks for the path so the investigator has the full
            per-file change context.
        max_chars: budget for the returned string. When the matched hunks
            exceed this, truncate with a trailing "\\n...[truncated]..." marker.
            Default 20000 matches the existing DeepSeekInvestigator default
            and the Profile schema default; callers can override.

    Returns:
        The matched hunks (including their `@@ ... @@` headers and a
        per-file header line) as a single string, or "" if the path is
        not found in `diff_text`.

    Behavior on edge cases:
    - Path not in diff → return "".
    - Line given but no hunk contains it → return all hunks for the path
      (the investigator gets the full context; better than empty).
    - Multiple hunks contain the line (shouldn't happen for a single anchor,
      but defensively): return all matching hunks.
    - File renamed (header shows `--- a/old/path` `+++ b/new/path`): match
      against the `b/` (new) side only.
    - Truncation: prefer keeping the hunk containing the line over distant
      hunks; if a single hunk exceeds max_chars, truncate at the boundary.
    """
    if not diff_text:
        return ""

    # Split into per-file blocks. Each block starts with "diff --git ...".
    # We split on "\ndiff --git " but need to handle the file that starts
    # at position 0 of the string.
    raw_blocks: list[str]
    if diff_text.startswith("diff --git "):
        raw_blocks = diff_text.split("\ndiff --git ")
        raw_blocks[0] = raw_blocks[0]  # already stripped of the leading marker
        raw_blocks = [raw_blocks[0]] + ["diff --git " + b for b in raw_blocks[1:]]
    else:
        parts = diff_text.split("\ndiff --git ")
        if len(parts) == 1:
            # No recognizable diff blocks found
            return ""
        raw_blocks = [parts[0]] + ["diff --git " + b for b in parts[1:]]

    target = f"b/{path}"

    for raw_block in raw_blocks:
        block_lines = raw_block.splitlines()
        if not block_lines:
            continue

        # The first line of a block is "diff --git a/... b/...".
        # We match against the b/ side.
        first_line = block_lines[0]
        if not first_line.startswith("diff --git "):
            continue

        # Extract the b/PATH from the diff header line.
        # Format: "diff --git a/PATH b/PATH"
        # Use rfind approach: split on " b/" from the right so renamed files
        # with spaces in their paths are handled correctly.
        b_idx = first_line.rfind(" b/")
        if b_idx == -1:
            continue
        b_path = first_line[b_idx + 1 :]  # "b/PATH"

        if b_path != target:
            continue

        # Found the matching file block.
        file_header, hunks = _parse_file_block(block_lines)

        if not hunks:
            # File matched but has no hunks (e.g., binary diff header only).
            result = "\n".join(file_header)
            if len(result) > max_chars:
                result = result[: max_chars - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER
            return result

        if line is None:
            # Return all hunks for the path.
            selected_hunks = hunks
        else:
            matching = [h for h in hunks if _hunk_contains_line(h, line)]
            selected_hunks = matching if matching else hunks

        result = _assemble(file_header, selected_hunks)

        if len(result) > max_chars:
            # Truncate: if there are priority hunks (line-matching), prefer them.
            if line is not None:
                priority = [h for h in selected_hunks if _hunk_contains_line(h, line)]
                if priority:
                    candidate = _assemble(file_header, priority)
                    if len(candidate) <= max_chars:
                        result = candidate
                    else:
                        result = (
                            candidate[: max_chars - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER
                        )
                    return result
            result = result[: max_chars - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER

        return result

    return ""
