# CHG-1826: Clearance Manual-Close Dedupe

**Applies to:** VOY project
**Last updated:** 2026-06-21
**Last reviewed:** 2026-06-21
**Status:** Proposed
**Date:** 2026-06-21
**Requested by:** Frank Xu via issue #197
**Priority:** P2
**Change Type:** Normal
**Targets:** `voyager/bots/clearance/close_reason.py`, `voyager/bots/clearance/pipeline.py`, Clearance tests
**Closes:** #197
**Related:** VOY-1813, OCO-2508, OCO-2509

---

## What

Add a narrow cross-head dedupe guard for Clearance Stage 1.5 manual-close
fallback replies when a review thread is semantically `RESOLVED`, GitHub still
shows it visually unresolved, `viewerCanResolve=false`, and no authorized
fallback resolver can call `resolveReviewThread`.

The fix must suppress repeated manual-close thread replies across new PR heads
only while the latest Clearance semantic state for that review thread remains
the same manual-close `RESOLVED` state.

## Why

Current close-reason markers are scoped to head SHA:

```text
clearance-close-reason:{thread.id}:{head_sha[:12]}
```

That is correct for current-head verdict evidence, but it means the unsupported
manual-close fallback can repost under the same review thread after every new
commit. The self-resolve and delegated-resolver paths avoid this because they
call `resolveReviewThread`; once GitHub reports `isResolved=true`, later heads
skip the thread. Manual-close does not mutate GitHub state, so it needs its own
idempotency rule.

## Out of Scope

- Changing normal `resolveReviewThread` behavior.
- Adding human or collaborator PR authors as fallback resolver identities.
- Suppressing OPEN or NEEDS_HUMAN_JUDGMENT review feedback.
- Changing PR-level Clearance summary update cadence.
- Removing head SHA from the existing `clearance-close-reason` marker globally.

## Surfaces

| # | Surface | Change |
|---|---------|--------|
| 1 | `voyager/bots/clearance/close_reason.py` | Add a dedicated manual-close marker helper that is distinct from `clearance-close-reason`. |
| 2 | `voyager/bots/clearance/pipeline.py` | In the `viewerCanResolve=false` manual-close branch, suppress duplicate thread replies only when the latest relevant Clearance semantic state is still manual-close RESOLVED. |
| 3 | Tests | Add regression coverage for unchanged RESOLVED across heads, RESOLVED -> OPEN -> RESOLVED, and out-of-order comment arrays ordered by `createdAt`. |

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Use a dedicated manual-close marker instead of broadening `clearance-close-reason`. | `clearance-close-reason` also appears in true resolve/delegated evidence. Reusing it for cross-head manual-close dedupe risks confusing successful resolution evidence with unsupported-capability guidance. |
| D2 | Dedupe by latest relevant Clearance semantic state, not by "thread ever had a manual-close marker." | A review thread can reopen with new feedback. RESOLVED -> OPEN -> RESOLVED must allow a fresh manual-close reply. |
| D3 | Use GitHub comment chronology such as `createdAt` to determine latest state. | Fixture array order is not a durable contract. The implementation must not pass only because test data happened to arrive sorted. |

## Implementation Plan

1. Add a manual-close marker helper, for example
   `clearance-manual-close:{thread_id}:...`, without changing the existing
   `clearance-close-reason:{thread_id}:{head}` marker contract.
2. Add a helper that scans Clearance-authored review-thread comments for
   relevant state markers and determines the latest state by `createdAt`.
3. In the manual-close fallback branch, suppress the reply only when the latest
   relevant state is the same manual-close `RESOLVED` state.
4. Ensure any later OPEN or NEEDS_HUMAN_JUDGMENT Clearance marker resets the
   suppression so a subsequent RESOLVED state can post again.
5. Keep PR-level Clearance summary updates unchanged.

## Testing / Verification

- Add or update unit coverage for marker helpers.
- Add BDD or unit coverage proving that the same thread with unchanged
  manual-close RESOLVED state across two head SHAs posts only once.
- Add coverage for RESOLVED -> OPEN -> RESOLVED proving the second RESOLVED
  manual-close reply is posted.
- Add coverage where comment array order is deliberately scrambled while
  `createdAt` preserves the true chronological order.
- Run the focused Clearance test subset.
- Run the project validation stack required by the implementation run.

## Rollback Plan

Revert the implementation commits for this CHG. Existing historical
manual-close comments remain harmless GitHub thread history. No data migration
is required because markers live in comments and the change should be additive
to parser logic.

## Acceptance Criteria

- [ ] Existing `clearance-close-reason` semantics remain head-scoped and are not
      repurposed as the manual-close dedupe key.
- [ ] Manual-close fallback replies are deduplicated across heads while the
      latest relevant Clearance state remains manual-close RESOLVED.
- [ ] RESOLVED -> OPEN -> RESOLVED emits a second manual-close reply.
- [ ] Dedupe uses reliable comment chronology such as `createdAt`, not array
      order.
- [ ] OPEN and NEEDS_HUMAN_JUDGMENT review feedback is never hidden by the
      manual-close dedupe.
- [ ] Focused tests and project validation pass.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-06-21 | Initial proposed CHG for issue #197 | Moth |
