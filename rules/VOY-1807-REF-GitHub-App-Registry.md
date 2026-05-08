# REF-1807: GitHub App Registry

**Applies to:** VOY project
**Last updated:** 2026-05-09
**Last reviewed:** 2026-05-09
**Status:** Active
**Related:** VOY-1805, VOY-1806, VOY-1808

---

## What Is It?

This registry records the actual GitHub Apps created under the `iterwheel`
organization for the Voyager bot roster.

---

## Content

| App | App ID | Public page | App webhook active | Private key | Installed repositories |
|-----|--------|-------------|--------------------|-------------|------------------------|
| `iterwheel-blueprint` | `3646512` | `https://github.com/apps/iterwheel-blueprint` | No | Stored on Wukong: `~/github-openclaw-agent/secrets/iterwheel-blueprint.private-key.pem` | `iterwheel/voyager`, `iterwheel/voyager-sandbox` (`130630088`); `frankyxhl/alfred`, `frankyxhl/babs`, `frankyxhl/fx_bin`, `frankyxhl/trinity` (`130696149`) |
| `iterwheel-stack` | `3646534` | `https://github.com/apps/iterwheel-stack` | No | Stored on Wukong: `~/github-openclaw-agent/secrets/iterwheel-stack.private-key.pem` | `iterwheel/voyager-sandbox` (`130630216`) |
| `iterwheel-staticfire` | `3646537` | `https://github.com/apps/iterwheel-staticfire` | No | Stored on Wukong: `~/github-openclaw-agent/secrets/iterwheel-staticfire.private-key.pem` | `iterwheel/voyager-sandbox` (`130630275`) |
| `iterwheel-clearance` | `3646538` | `https://github.com/apps/iterwheel-clearance` | No | Stored on Wukong: `~/github-openclaw-agent/secrets/iterwheel-clearance.private-key.pem` | `iterwheel/voyager-sandbox` (`130630338`) |
| `iterwheel-countdown` | `3646540` | `https://github.com/apps/iterwheel-countdown` | No | Stored on Wukong: `~/github-openclaw-agent/secrets/iterwheel-countdown.private-key.pem` | `iterwheel/voyager-sandbox` (`130630407`) |

Current repository event source:

| Repository | Webhook ID | URL | Active | Events | Last delivery state |
|------------|------------|-----|--------|--------|---------------------|
| `iterwheel/voyager-sandbox` | `619824421` | `https://gh.iterwheel.com/github/webhook` | Yes | `check_run`, `check_suite`, `issues`, `issue_comment`, `label`, `pull_request`, `pull_request_review`, `pull_request_review_comment`, `status`, `workflow_run` | `200 OK` |
| `iterwheel/voyager` | `619976821` | `https://gh.iterwheel.com/github/webhook` | Yes | `issues`, `issue_comment` | `200 OK` |
| `frankyxhl/alfred` | `619961538` | `https://gh.iterwheel.com/github/webhook` | Yes | `issues`, `issue_comment` | `200 OK` |
| `frankyxhl/babs` | `619961554` | `https://gh.iterwheel.com/github/webhook` | Yes | `issues`, `issue_comment` | `200 OK` |
| `frankyxhl/fx_bin` | `619961564` | `https://gh.iterwheel.com/github/webhook` | Yes | `issues`, `issue_comment` | `200 OK` |
| `frankyxhl/trinity` | `619959453` | `https://gh.iterwheel.com/github/webhook` | Yes | `issues`, `issue_comment` | `200 OK` |

Current bridge write-back:

| Agent | Repository scope | Trigger | Write-back |
|-------|------------------|---------|------------|
| `iterwheel-blueprint` | `iterwheel/voyager`, `iterwheel/voyager-sandbox`, `frankyxhl/alfred`, `frankyxhl/babs`, `frankyxhl/fx_bin`, `frankyxhl/trinity` | `issues.opened`, `issues.edited`, `issues.reopened`, or `/blueprint` issue comment | Validates issue title format and intake fields, maintains exactly one Blueprint state label from `blueprint-needed`, `blueprint-ready`, and `blueprint-requests-revision`, upserts one Blueprint intake comment, and adds a `rocket` issue reaction when the issue is Blueprint-ready |
| `iterwheel-stack` | `iterwheel/voyager-sandbox` | `issues.opened`, `issues.edited`, `issues.reopened`, `pull_request.opened`, `pull_request.edited`, `pull_request.reopened`, `pull_request.ready_for_review`, `pull_request.synchronize`, or `/stack` issue comment | Maintains one `stack-type-*`, one `stack-area-*`, one `stack-size-*`, and one `stack-risk-*` classification label when confident; otherwise applies `stack-needs-review`; upserts one Stack classification comment; adds `rocket` on successful classification and `eyes` when human review is needed |

Cross-account installation:

| Account | Repository | Strategy | Status |
|---------|------------|----------|--------|
| `frankyxhl` | `frankyxhl/alfred`, `frankyxhl/babs`, `frankyxhl/fx_bin`, `frankyxhl/trinity` | Reuse existing `iterwheel-*` Apps by making them installable on selected repositories outside the owning organization. | `iterwheel-blueprint` installed as selected-repository installation `130696149`; other Apps remain sandbox-only |

Operational notes:

- `iterwheel-blueprint` was first created as `iw-blueprint`, then renamed after
  `iw-stack` collided with an existing GitHub account.
- `iterwheel-blueprint` is public so it can be installed outside the
  `iterwheel` organization, but it is not Marketplace-listed.
- App webhooks remain disabled. Enabling them after creation did not persist in
  the GitHub UI, and the App hook configuration API returned no hook entity for
  apps that were originally created webhook-disabled.
- A repository-level webhook is the current bootstrap event source for
  allow-listed repositories. The five GitHub Apps still provide the per-agent
  write-back identities and permission boundaries.
- The local bridge is listening on Wukong at `127.0.0.1:8787`, and
  `https://gh.iterwheel.com/healthz` succeeds through the Cloudflare tunnel.
- The bridge now runs with `BRIDGE_DRY_RUN=false` for
  explicitly allow-listed repositories. Installation access tokens are
  generated on demand in memory and are not written to disk.
- Each app has exactly one active private key in GitHub. Earlier uncaptured keys
  from the first browser automation attempt were deleted.
- Private key files are stored outside git on Wukong with `600` file
  permissions. Local downloaded `.pem` copies were removed after transfer.
- Repository installation started with the selected private test repository
  `iterwheel/voyager-sandbox`.

---

## Change History

| Date       | Change                                                                                                            | By               |
|------------|-------------------------------------------------------------------------------------------------------------------|------------------|
| 2026-05-09 | Initial version - recorded created Iterwheel GitHub Apps and current activation state                             | Frank Xu + Codex |
| 2026-05-09 | Generated private keys, stored them on Wukong, removed local downloaded copies, and deleted uncaptured stale keys | Frank Xu + Codex |
| 2026-05-09 | Installed all five Apps on `iterwheel/voyager-sandbox` and recorded repository webhook bootstrap state            | Frank Xu + Codex |
| 2026-05-09 | Enabled `iterwheel-blueprint` issue label/comment write-back for the sandbox repository                           | Frank Xu + Codex |
| 2026-05-09 | Recorded planned cross-account installation path for `frankyxhl/trinity`                                          | Frank Xu + Codex |
| 2026-05-09 | Made `iterwheel-blueprint` public, installed it on selected `frankyxhl` repositories, and verified `trinity` #77  | Frank Xu + Codex |
| 2026-05-09 | Added repository webhooks and Blueprint labels for `frankyxhl/alfred`, `frankyxhl/babs`, and `frankyxhl/fx_bin`   | Frank Xu + Codex |
| 2026-05-09 | Enabled Blueprint ready-state `rocket` issue reactions and verified it on `frankyxhl/trinity` #77                 | Frank Xu + Codex |
| 2026-05-09 | Added `iterwheel/voyager` to Blueprint installation, webhook allow-list, and issue title validation smoke test    | Frank Xu + Codex |
| 2026-05-09 | Standardized Blueprint issue-state labels and removed the older `needs-blueprint` name from the registry          | Frank Xu + Codex |
| 2026-05-09 | Tightened Blueprint write-back so only one Blueprint state label is active at a time                              | Frank Xu + Codex |
| 2026-05-09 | Added Stack v1 sandbox write-back scope for deterministic classification labels and `eyes` reactions              | Frank Xu + Codex |
| 2026-05-09 | Added Stack low-confidence `stack-needs-review`, upserted comments, and success `rocket` reactions                | Frank Xu + Codex |
