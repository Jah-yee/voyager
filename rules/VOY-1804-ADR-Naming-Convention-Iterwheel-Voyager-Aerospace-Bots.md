# ADR-1804: Naming Convention — Iterwheel + Voyager + Aerospace Bots

**Applies to:** VOY project
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Accepted
**Related:** VOY-1800, VOY-1801, VOY-1802, VOY-1803

---

## What Is It?

A record of the reasoning behind three core naming decisions:

1. **Organization name** = Iterwheel (Iteration + Flywheel)
2. **First project name** = Voyager (the long-range probe)
3. **Bot naming system** = rocket launch narrative (Blueprint → Liftoff)

> **This ADR is not a rulebook — it is the "flight data recorder" of our decisions.**
> Future readers should be able to understand why we chose this and which paths we ruled out.

---

## Context

When starting a new multi-agent / GitHub automation project, we needed a unified
naming system. Requirements:

- Spans organization → project → component, three layers
- Holds room for future expansion (new bots, sister projects, version bumps)
- Has narrative weight and ceremony — not just functional naming
- Aligns with our core belief in the AI era: knowledge compounds, capability is a flywheel

Candidates considered along the way:

| Direction | Style | Example | Why rejected |
|-----------|-------|---------|--------------|
| Philosophical | Math / limits | Asymptote | Abstract, low visual punch |
| Zen | Eastern philosophy | Shu-Ha-Ri | Hard to internationalize, hard to coin words from |
| Jazz | Musical improvisation | Cadenza | Romantic but lacks forward momentum |
| Mechanical | Single image | Flywheel | Insufficient — cannot express both "iteration" and "accumulation" |

---

## Decision

### 1. Organization name: Iterwheel

**Iterwheel** = **Iter**(ation) + (Fly)**wheel**

Why this won:

- Carries both "iteration" (stepwise improvement) and "flywheel" (cumulative momentum) at once
- A coined word — memorable and easy to brand independently
- Clear metaphor: "every iteration adds a little kinetic energy to the flywheel"

### 2. First project name: Voyager

Why Voyager rather than Pioneer / Cassini / Hayabusa (full reasoning in VOY-1801):

- **Strongest sense of compounding** — actually flew for nearly 50 years and is still working
- **Gravity assist** — perfectly matches Iterwheel's "flywheel acceleration" metaphor
- **Golden Record** — gives a poetic anchor for "release as a container for the future"
- **Autonomous operation** — aligns with the engineering philosophy of remote-autonomous multi-agent systems

### 3. Bot naming system: rocket launch narrative

Iteration history:

1. First tried a **flywheel-parts family**: Spoke / Hub / Bearing / Tourbillon
   - Problem: too abstract, too "mechanical" — no narrative arc
2. Then realized the Release Bot should mean "ignite / start" → explored Spark / Ignite / Flint
   - Problem: solves only the endpoint; cannot tie the whole pipeline together
3. Finally upgraded to the **rocket narrative family**:
   Blueprint → Stack → Static Fire → Clearance → Countdown → Liftoff
   - Complete narrative arc: from blueprint to launch, every stage maps to a real aerospace term
   - Satisfies all five principles in VOY-1800 §Design Principles

---

## Consequences

### Positive

- ✅ Naming flows across organization → project → bot, narrative-consistent (VOY-1800 P1)
- ✅ Easy future expansion: new bots find a rocket-stage word; new projects find a space-mission name
- ✅ Reserved expansion slots already prepared: Manifest / Caliper / Tanking / Apogee / Telemetry
- ✅ Voyager II / Pioneer / New Horizons / Cassini / Hayabusa already reserved as sister-project codenames

### Negative / Trade-offs

- ⚠️ All-English aerospace terms reduce readability for purely Chinese-language contexts
  (accepted; aerospace English remains the canonical form)
- ⚠️ The rocket narrative restricts us to one family of metaphors — if a future bot is
  truly "non-rocket" in nature, it needs a fresh ADR justifying the exception
  (per VOY-1800 §Design Principles #1)
- ⚠️ Once the naming system is widely adopted, renaming costs become high — which is
  precisely why this ADR exists

### Triggers for Revisiting

The following situations require a new ADR amending this decision:

- A new bot has no plausible rocket-stage word
- A core subsystem appears that conflicts with the rocket narrative (e.g., a pure data
  or pure observability mega-module)
- The organization or project layer wants to rename

---

## Meta: The Flywheel of Thinking

> The naming process itself is the best demonstration of the Iterwheel spirit —
> iteration after iteration, each version sharper than the last, until the flywheel finally spins.

This is recorded not as self-praise but as a reminder: when naming the next thing,
**give yourself permission to iterate. Do not chase a one-shot answer.**

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — extracted from `Iterwheel-Founding-Document.md` v1.1 (Naming & Reasoning section) and promoted to Accepted | Claude Code |
| 2026-05-09 | Translated to English (project standard: English-only docs) | Claude Code |
