# SOP-1805: GitHub Bot Accounts and Responsibilities

**Applies to:** VOY project
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Active
**Related:** VOY-1802, VOY-1804

---

## What Is It?

This SOP records the first public GitHub bot account roster for Iterwheel's
Voyager automation pipeline: account handles, display names, stage
responsibilities, and permission boundaries.


## Why

GitHub bot accounts are publicly visible through organization membership, issue
comments, pull request reviews, status checks, and audit trails. Their names
must therefore be readable as public product surface, not just internal utility
labels.

The account handles use a short `iw-` prefix for GitHub ergonomics while keeping
the canonical aerospace display names from VOY-1802 and VOY-1804.

---

## When to Use

- Creating or inviting Iterwheel-owned GitHub bot accounts.
- Assigning bot accounts to GitHub teams or repositories.
- Explaining which bot should comment on an issue, review a pull request, or
  publish a gate verdict.
- Reviewing whether a proposed new bot overlaps with an existing stage.


## When NOT to Use

- Naming non-GitHub services, internal processes, or local-only agents that do
  not appear publicly on GitHub.
- Granting production deploy or repository administration authority. Those
  permissions require a separate ADR and explicit approval.
- Renaming the canonical aerospace stage names from VOY-1802. Use a new ADR for
  any naming-system change.


## Steps

1. **Use the canonical first-batch roster**

   | GitHub handle | Display name | Primary responsibility |
   |---------------|--------------|------------------------|
   | `iw-blueprint` | Blueprint | Issue intake: validate issue templates, completeness, labels, priority hints, and missing context. |
   | `iw-stack` | Stack | PR intake: validate pull request title, body, linked issue, declared scope, and repository-specific conventions. |
   | `iw-staticfire` | Static Fire | CI and test aggregation: read checks, lint, typecheck, test, and workflow results; summarize failures in human-readable form. |
   | `iw-clearance` | Clearance | Review readiness: aggregate approvals, requested changes, unresolved review threads, and bot verdicts. |
   | `iw-countdown` | Countdown | Final merge gate: publish a GO or HOLD verdict after checking CI, review state, branch protection, conflicts, and release constraints. |

2. **Keep handle rules stable**

   - Use `iw-` as the GitHub account prefix.
   - Use lowercase ASCII handles.
   - Prefer exactly one hyphen after `iw`.
   - Do not add extra internal hyphens unless readability requires it.
   - Preserve canonical display names with normal spacing, such as `Static Fire`.

3. **Treat `iw-staticfire` as the handle exception**

   The canonical display name remains `Static Fire`, but the GitHub handle is
   `iw-staticfire` rather than `iw-static-fire` to keep the public handle shorter
   and visually cleaner.

4. **Limit initial authority**

   The first-batch accounts may read repository state, post comments, publish
   check/status conclusions, and participate in review workflows. They must not
   receive broad organization administration, repository administration,
   billing, secret-management, or direct production-deploy authority by default.

5. **Treat Countdown as advisory until hardened**

   `iw-countdown` is the desired final merge gate, but its first operating mode
   is advisory: it may publish `GO` or `HOLD` conclusions, while actual merge
   authority remains with humans, GitHub branch protection, or a later approved
   automation design.

---

## Change History

| Date       | Change                                                                                                                       | By               |
|------------|------------------------------------------------------------------------------------------------------------------------------|------------------|
| 2026-05-09 | Initial version - recorded first-batch public GitHub bot handles, display names, responsibilities, and permission boundaries | Frank Xu + Codex |
