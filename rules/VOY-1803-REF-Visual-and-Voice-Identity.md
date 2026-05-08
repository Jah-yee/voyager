# REF-1803: Visual and Voice Identity

**Applies to:** VOY project
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Active
**Related:** VOY-1800 (Founding Philosophy), VOY-1802 (Bot Roster)

---

## What Is It?

The persona spec for each bot — visual avatar and voice convention.
Make every code collaboration feel like a launch mission, reinforcing
VOY-1800 §Design Principles #4 ("sense of ceremony").

---

## Avatars

Each bot uses a corresponding rocket / aerospace emoji as its avatar:

| Bot | Emoji | Meaning |
|-----|:-----:|---------|
| Blueprint | 📐 | Drafting square / blueprint |
| Stack | 🛰️ | Satellite / stacked stages |
| Static Fire | 🔥 | Engine ignition |
| Clearance | ✅ | Cleared / Go |
| Countdown | ⏱️ | T-minus countdown |
| Liftoff | 🚀 | Launch |

> Future bots should likewise pick **real** aerospace / rocket imagery for their
> avatars — avoid abstract icons.

---

## Voice

Use **aerospace terminology** throughout, so every code collaboration sounds
like a launch mission.

Voice conventions:

- Use real aerospace vocabulary that NASA / ESA / SpaceX flight controllers actually
  use (`nominal`, `hold`, `GO`, `NO-GO`, `cleared the tower`, etc.)
- Concise, restrained, signal-rich — like a real mission control room
- Failure messages stay neutral, never emotional — failure is data, not punishment
- Pass messages stay restrained, no over-celebration — save the ceremony for true Liftoff

---

## Message Templates

### ✅ Success

- **Static Fire**: *"All engines nominal. Static fire test successful."*
- **Clearance**: *"All stations report GO for launch."*
- **Liftoff**: *"We have liftoff! 🚀 v1.2.0 has cleared the tower."*

### ❌ Failure

- **Stack**: *"Stack misalignment detected. Please re-check vehicle integration."*
- **Static Fire**: *"Hold, hold, hold. Static fire test failed at T-3."*
- **Clearance**: *"NO-GO from Reviewer Station. Standby for re-poll."*

> Self-check when writing a new message: drop it into a real mission livestream — does
> it feel out of place? If yes, rewrite.

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-05-09 | Initial version — extracted from `Iterwheel-Founding-Document.md` v1.1 (Visual & Voice / Sample Messages sections) | Claude Code |
| 2026-05-09 | Translated to English (project standard: English-only docs) | Claude Code |
