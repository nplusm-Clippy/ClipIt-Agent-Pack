---
name: clipper-social-publishing
description: Inspect authorized social accounts and post, schedule, monitor, or cancel an exact-current ClipIt export with explicit artifact, account, copy, timing, and spend approval. Use for any social delivery or publishing-status request.
license: MIT
metadata:
  version: "2.0.0"
  tags: [Video, ClipIt, Social Media, TikTok, YouTube, Instagram, Publishing, Scheduling]
  hermes:
    tags: [Video, ClipIt, Social Media, TikTok, YouTube, Instagram, Publishing, Scheduling]
    requires_toolsets: [terminal]
---

# ClipIt Social Publishing

Use with `clipit-operator` and `delivery-qa`. Prefer current `clipit social` commands or discovered MCP tools; use these Python scripts as the exact REST fallback. Refresh account IDs and delivery state immediately before every publish/schedule mutation.

## When to Use

Use this skill when the user wants to:
- Post a rendered clip to social media immediately
- Schedule a clip for future posting
- Check the status of a published or scheduled post
- Cancel a scheduled post
- See which social accounts are connected

**Supported platforms:** YouTube, TikTok, Instagram, Facebook, LinkedIn, Twitter/X, Bluesky, Threads, Pinterest, Reddit, Telegram, Snapchat, Google Business.

**Prerequisite:** The clip MUST have one completed export that exactly matches its current canonical editor snapshot. For enterprise, use the exact-delivery recipe so style, export lineage, outro policy, artifact duration, and ready-deliverable state are verified together; the client must then select it in the portal. Confirm authority with the named profile and `list_deliverables.py --status selected`.

**Account setup:** Ordinary users connect accounts in ClipIt Settings. Enterprise clients connect accounts in their workspace portal, and an admin grants the exact accounts that Hermes may use. The API cannot connect or grant accounts; it can only list and publish through already-connected/authorized accounts.

**Enterprise identity:** Enterprise keys are ClipIt-team-only. Select the workspace's distinct non-default CLI profile with `CLIPIT_PROFILE`, then run `verify_enterprise_workspace.py --workspace-id <expected-id>` before listing accounts or publishing. Keep that profile selected for the whole client session. Never put a workspace key in the shared Hermes `CLIPPER_API_KEY` environment variable.

**Publishing authority:** Always list accounts immediately before publishing and pin the returned `accountId`. Enterprise workspace keys support one exact platform/account per publish or schedule request. Ordinary keys may still publish to multiple platforms when every platform has an exact account pin.

**API key permissions:** The scripts require both `social_publishing` and `clip_generation`; `clip_generation` is needed to read canonical delivery-state before the publish call.

Run a live preflight and apply an approved cap before an ordinary-key post. Enterprise workspace posts report internal usage separately from `clientCreditChargeClip: 0`.

## Quick Reference

| Operation | Preferred path | REST fallback |
|-----------|----------------|---------------|
| List accounts | `clipit social accounts --json` | `list_social_accounts.py` |
| Check selected enterprise delivery | `clipit deliverables list --status selected --json` | `list_deliverables.py --status selected` |
| Post/schedule | `clipit social post|schedule ... --confirm --max-credits <cap> --json` | `post_to_social.py`; `schedule_social_post.py` |
| Status/cancel | `clipit social get|cancel ...` | `get_social_post.py`; `cancel_social_post.py` |

## Procedure

### Checking Connected Accounts

**When to use:** Before posting, verify which platforms the user has connected.

**Steps:**
1. Run `python scripts/list_social_accounts.py`
2. Each authorized entry shows `platform`, `connected`, `accountId`, and `accountName`. Copy the exact `accountId`; names are display-only and are not publishing authority.
3. For an enterprise key, this list contains only accounts actively granted to that workspace. If the account is missing, have the client connect it in the workspace portal and have an admin grant it.
4. For an ordinary key, direct the user to https://clipit.dev/settings/social when the target account is not connected.

### Posting a Clip Immediately

**When to use:** The user says "post this to TikTok" or "share on Instagram."

**Prerequisites:**
- For enterprise, the named-profile identity preflight MUST match the exact active workspace before any account or clip lookup.
- The clip MUST have a verified exact-current completed export. If it does not, save the editor state, start an export, and wait for completion.
- The exact target account MUST appear in `list_social_accounts.py` immediately before publishing.
- For enterprise, the clip/export must belong to a client-selected deliverable and the target account grant must still be active.

**Steps:**
1. For enterprise, run `python scripts/list_deliverables.py --workspace-id <id> --profile <name> --status selected --export-id <id>` and confirm the exact export is selected.
2. Run `python scripts/list_social_accounts.py` and copy the exact `accountId` for the intended platform.
3. Present the exact current artifact, account, caption/title, immediate timing, live estimate, and cap; obtain publish approval.
4. Prefer `clipit social post ... --confirm --max-credits <cap> --json`; use `post_to_social.py` only as the approved REST fallback.
5. If delivery-state reports multiple exact-current exports, pin one with `--export-id <id>`.
6. For YouTube, include the current required title field.
7. The fallback automatically pins export/snapshot/output/account identity. Never hand-build or weaken those pins.

**Example:**
```bash
python scripts/post_to_social.py \
  --clip-id clip_xyz \
  --platform linkedin \
  --account-id account_linkedin_123 \
  --export-id export_xyz \
  --caption "This is the best moment from today's stream! #viral #clips" \
  --hashtags "viral,clips,gaming" \
  --wait
```

Ordinary keys retain multi-platform support:

```bash
python scripts/post_to_social.py \
  --clip-id clip_xyz \
  --platforms tiktok,instagram \
  --account-ids tiktok=account_tt_123,instagram=account_ig_456 \
  --caption "Best moment" \
  --wait
```

### Scheduling a Post

**When to use:** The user wants to post at a specific time (e.g., "post tomorrow at 9am").

**Steps:**
1. Refresh `list_social_accounts.py` and copy the exact authorized `accountId`.
2. Present the exact artifact/account/copy/time zone/time, live estimate, and cap; obtain schedule approval.
3. Prefer `clipit social schedule ... --confirm --max-credits <cap> --json`; use `schedule_social_post.py` only as the approved REST fallback.
4. Add `--export-id <id>` when delivery-state has more than one exact-current export.
5. Enterprise schedules use one exact platform/account request and usage-only settlement.
6. The scheduled timestamp must be in the future and include an explicit timezone.
7. Retain any returned job ID and wait/resume the same schedule request.

### Checking Post Status

**When to use:** The user asks "did it post?" or you need to verify a post succeeded.

**Steps:**
1. Run `python scripts/get_social_post.py --post-id <id>`
2. Status values: `pending` → `posting` → `posted` (success) or `failed`
3. For scheduled posts: `scheduled` → `posting` → `posted` or `failed`
4. The `perPlatformResults` field shows success/failure per platform with individual post URLs

### Cancelling a Scheduled Post

**When to use:** The user wants to cancel a post before it goes out.

**Steps:**
1. Re-read the exact post and obtain cancellation approval for its ID/account/time.
2. Prefer `clipit social cancel <id> --confirm --json`; use the script only as an approved fallback.
3. Cancellation applies only before the post has completed; verify the returned final state.

## Pitfalls

- **Exact export identity is mandatory.** A render status alone is insufficient. The scripts refuse stale, ambiguous, unverified, or non-current exports; use `--export-id` only to choose among completed exports that exactly match the current editor snapshot.
- **Never identify an account by display name.** Refresh `list_social_accounts.py` and pin its exact `accountId`. Revoked enterprise grants disappear from this list.
- **Enterprise means one account per request.** Run a separate approved request for each platform/account. Do not combine enterprise platforms.
- **Enterprise identity must be proven first.** A successful personal-library request is not workspace proof; require `verify_enterprise_workspace.py` for the expected workspace ID.
- **Agents cannot select client authority.** The recipe and `deliver_export.py` create `ready` only. Wait for the client to select in the portal and verify `selected` with the same named profile.
- **YouTube requires `--title`.** If you're posting to YouTube without a title, the API returns 400. Always include `--title` when YouTube is in the platforms list.
- **Do not use remembered publishing prices.** Preflight the exact artifact/destinations under the active profile and confirm against the approved cap. Enterprise usage-only settlement records usage without client debit.
- **Scheduled posts aren't free to cancel.** While no credits are charged until the post fires, cancelling at the last second might not work if the post is already in the posting queue.
- **Platform limits change.** Use current platform validation/tool output for titles, captions, hashtags, duration, and scheduling constraints.
- **Social setup stays in the web UI.** You cannot connect or grant an account through these scripts. Ordinary users use Settings; enterprise clients and admins use the enterprise portal/workspace controls.

## Verification

- **Post succeeded:** `status === "posted"` and `perPlatformResults` shows success for each platform
- **Post URL available:** Each platform's result includes a `postUrl` linking to the published content
- **Schedule created:** Response has `status === "scheduled"` and `scheduledFor` matches the requested time
- **Cancel succeeded:** Post status changes to `cancelled`
- **Failed post:** Check `perPlatformResults` for per-platform error messages — some platforms may succeed while others fail
