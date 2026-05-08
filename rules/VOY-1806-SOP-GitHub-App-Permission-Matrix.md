# SOP-1806: GitHub App Permission Matrix

**Applies to:** VOY project
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Active
**Related:** VOY-1802, VOY-1804, VOY-1805

---

## What Is It?

This SOP defines the initial GitHub App permission matrix for the first
Iterwheel Voyager bot roster. It maps each public bot identity to the minimum
repository permissions and webhook events needed for its first operating mode.


## Why

GitHub App permissions are security boundaries. They decide which repository
resources a bot can read, write, and receive webhook notifications for. The
Voyager bots must start with narrowly scoped permissions: enough to comment,
publish checks, and report gate verdicts, but not enough to administer
repositories, manage secrets, deploy production, or merge code directly.

---

## When to Use

- Creating the first-batch GitHub Apps for the Iterwheel organization.
- Reviewing whether a bot needs additional GitHub API access.
- Installing a GitHub App onto selected repositories.
- Auditing why an app was granted a specific permission or webhook event.


## When NOT to Use

- Granting repository administration, organization administration, billing,
  secrets, deployments, or production-write permissions.
- Designing automatic merge authority for `iw-countdown`. That requires a
  separate ADR and hardened implementation.
- Replacing GitHub branch protection. The Countdown bot publishes a verdict; it
  does not substitute for protected-branch policy.


## Steps

1. **Create one GitHub App per public bot identity**

   Use separate GitHub Apps so public GitHub actions can appear under distinct
   bot names such as `iw-blueprint[bot]` and `iw-countdown[bot]`.

   | GitHub App name | Display stage | First operating mode |
   |-----------------|---------------|----------------------|
   | `iw-blueprint` | Blueprint | Issue intake and triage comments. |
   | `iw-stack` | Stack | Pull request intake and structure checks. |
   | `iw-staticfire` | Static Fire | CI, test, workflow, and check aggregation. |
   | `iw-clearance` | Clearance | Review readiness aggregation. |
   | `iw-countdown` | Countdown | Final advisory GO/HOLD merge gate. |

2. **Use common app settings**

   | Setting | Value |
   |---------|-------|
   | Owner | `iterwheel` organization |
   | Homepage URL | `https://github.com/iterwheel` |
   | Webhook active | Yes |
   | Webhook URL | `https://gh.iterwheel.com/github/webhook` |
   | SSL verification | Enabled |
   | Installation visibility | Only on this account |
   | Initial repository installation | Only selected test repositories |
   | User authorization during installation | Disabled unless a later design requires user-scoped API calls |

   Each app should use its own webhook secret and private key. Secrets and
   private keys must be stored outside git with `600` file permissions.

3. **Grant the first-batch repository permissions**

   | App | Metadata | Contents | Issues | Pull requests | Checks | Actions | Commit statuses |
   |-----|----------|----------|--------|---------------|--------|---------|-----------------|
   | `iw-blueprint` | Read | No access | Read & write | No access | Read & write | No access | No access |
   | `iw-stack` | Read | Read-only | Read & write | Read & write | Read & write | No access | No access |
   | `iw-staticfire` | Read | Read-only | No access | Read-only | Read & write | Read-only | Read-only |
   | `iw-clearance` | Read | Read-only | Read & write | Read & write | Read & write | No access | Read-only |
   | `iw-countdown` | Read | Read-only | Read & write | Read-only | Read & write | Read-only | Read-only |

   Notes:

   - `Metadata: read` is the baseline repository visibility permission.
   - `Contents: read-only` allows PR-context and repository file reads without
     granting code write access.
   - `Issues: read & write` allows issue comments, labels, and PR comments that
     flow through issue APIs.
   - `Pull requests: read & write` allows PR review workflow participation for
     Stack and Clearance. Countdown starts at read-only because it should publish
     advisory checks/comments, not approve or merge.
   - `Checks: read & write` allows each bot that publishes a verdict to create
     check runs.
   - `Actions: read-only` and `Commit statuses: read-only` are reserved for bots
     that summarize CI or gate readiness.

4. **Subscribe to webhook events**

   | App | Events |
   |-----|--------|
   | `iw-blueprint` | Issues, Issue comment |
   | `iw-stack` | Pull request, Issue comment |
   | `iw-staticfire` | Check run, Check suite, Status, Workflow run, Pull request |
   | `iw-clearance` | Pull request, Pull request review, Pull request review comment, Issue comment |
   | `iw-countdown` | Pull request, Pull request review, Pull request review comment, Check run, Check suite, Status, Workflow run, Issue comment |

5. **Do not grant dangerous defaults**

   The first-batch apps must not receive these permissions by default:

   - Administration
   - Secrets
   - Codespaces secrets
   - Dependabot secrets
   - Environments
   - Deployments
   - Workflows write access
   - Contents write access
   - Organization administration
   - Billing or plan access

6. **Install cautiously**

   Install each app only on selected test repositories at first. Expand
   repository access after webhook delivery, signature verification, event
   routing, and dry-run publishing are proven.


## Examples

### First safe installation

Create `iw-countdown` with the permissions in this SOP, install it only on one
non-critical repository, and configure branch protection to require the
Countdown check without giving the app merge or contents-write authority.

### Permission escalation request

If `iw-countdown` later needs to merge pull requests directly, do not edit this
SOP in place. Write a new ADR describing the exact merge mechanism, branch
protection interaction, rollback behavior, audit trail, and failure modes.

---

## Change History

| Date       | Change                                                                                                   | By               |
|------------|----------------------------------------------------------------------------------------------------------|------------------|
| 2026-05-09 | Initial version - recorded per-bot GitHub App permissions, webhook events, and denied dangerous defaults | Frank Xu + Codex |
