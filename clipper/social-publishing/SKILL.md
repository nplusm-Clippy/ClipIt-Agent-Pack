---
name: clipper-social-publishing
description: Post and schedule clips to 13 social media platforms via ClipIt
version: 1.3.0
author: nplusm-Clippy
license: MIT
platforms: [macos, linux, windows]
metadata:
  tags: [Video, ClipIt, Social Media, TikTok, YouTube, Instagram, Publishing, Scheduling]
  hermes:
    tags: [Video, ClipIt, Social Media, TikTok, YouTube, Instagram, Publishing, Scheduling]
    requires_toolsets: [terminal]
required_environment_variables:
  - name: CLIPPER_API_KEY
    prompt: "Enter your ClipIt API key"
    help: "Get one at https://clipit.dev -> Settings -> API Keys -> Quick Connect"
    required_for: "ClipIt API access"
---

# ClipIt Social Publishing

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

Use account-insights before an ordinary-key post: `get_credits_balance.py` shows available $CLIP and `estimate_cost.py` can preflight known publishing costs. Enterprise workspace posts record usage for reporting but debit 0 client $CLIP credits.

## Quick Reference

| Operation | Script | Cost |
|-----------|--------|------|
| List connected accounts | `list_social_accounts.py` | Free |
| Check selected enterprise deliveries | `list_deliverables.py --workspace-id <id> --profile <name> --status selected` | Free |
| Post immediately | `post_to_social.py --clip-id <id> --platform linkedin --account-id <accountId> --caption "..." [--export-id <id>] [--wait]` | Ordinary: 65 $CLIP/platform; enterprise: usage-only, 0 client debit |
| Schedule post | `schedule_social_post.py --clip-id <id> --platform linkedin --account-id <accountId> --caption "..." --scheduled-for <iso> [--export-id <id>]` | Ordinary: billed at post time; enterprise: usage-only, 0 client debit |
| Check post status | `get_social_post.py --post-id <id>` | Free |
| Cancel scheduled post | `cancel_social_post.py --post-id <id>` | Free |

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
3. Run `python scripts/post_to_social.py --clip-id <id> --platform linkedin --account-id <accountId> --caption "Your caption here" --wait`.
4. If delivery-state reports multiple exact-current exports, rerun with `--export-id <id>` to select one explicitly.
5. For YouTube, include `--title "Video Title"`.
6. The script automatically reads delivery-state and sends `exportId`, `expectedSnapshotId`, `expectedOutputObjectFingerprint`, `expectedAccountIds`, and `publishExactCurrentArtifact=true`. Never hand-build or weaken those pins.

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
2. Run `python scripts/schedule_social_post.py --clip-id <id> --platform tiktok --account-id <accountId> --caption "..." --scheduled-for "2030-04-15T09:00:00Z" --wait`.
3. Add `--export-id <id>` when delivery-state has more than one exact-current export.
4. Enterprise schedules use one exact platform/account request and record usage without debiting client credits.
5. The `--scheduled-for` value MUST be in the future (ISO 8601 format with timezone).
6. Ordinary-key credits are not charged at scheduling time; they are charged when the post fires.
7. The response includes either a completed schedule record or a `jobId`; `--wait` follows enterprise schedule registration jobs.

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
1. Run `python scripts/cancel_social_post.py --post-id <id>`
2. Only works on `scheduled` or `pending` status — cannot cancel already-posted content
3. If the post was already sent to the scheduling queue, it's also cancelled there

## Pitfalls

- **Exact export identity is mandatory.** A render status alone is insufficient. The scripts refuse stale, ambiguous, unverified, or non-current exports; use `--export-id` only to choose among completed exports that exactly match the current editor snapshot.
- **Never identify an account by display name.** Refresh `list_social_accounts.py` and pin its exact `accountId`. Revoked enterprise grants disappear from this list.
- **Enterprise means one account per request.** Run a separate approved request for each platform/account. Do not combine enterprise platforms.
- **Enterprise identity must be proven first.** A successful personal-library request is not workspace proof; require `verify_enterprise_workspace.py` for the expected workspace ID.
- **Agents cannot select client authority.** The recipe and `deliver_export.py` create `ready` only. Wait for the client to select in the portal and verify `selected` with the same named profile.
- **YouTube requires `--title`.** If you're posting to YouTube without a title, the API returns 400. Always include `--title` when YouTube is in the platforms list.
- **Ordinary posts cost 65 $CLIP per platform.** Check account-insights and confirm before publishing. Enterprise workspace keys use `enterprise_usage_only`: usage is measured but the client balance is not debited.
- **Scheduled posts aren't free to cancel.** While no credits are charged until the post fires, cancelling at the last second might not work if the post is already in the posting queue.
- **Platform-specific character limits.** Twitter/X: 280 chars, TikTok: 2200 chars, Instagram: 2200 chars. The API validates these but it's better to respect them upfront.
- **Social setup stays in the web UI.** You cannot connect or grant an account through these scripts. Ordinary users use Settings; enterprise clients and admins use the enterprise portal/workspace controls.

## Verification

- **Post succeeded:** `status === "posted"` and `perPlatformResults` shows success for each platform
- **Post URL available:** Each platform's result includes a `postUrl` linking to the published content
- **Schedule created:** Response has `status === "scheduled"` and `scheduledFor` matches the requested time
- **Cancel succeeded:** Post status changes to `cancelled`
- **Failed post:** Check `perPlatformResults` for per-platform error messages — some platforms may succeed while others fail
