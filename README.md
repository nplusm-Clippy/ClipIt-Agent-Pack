# ClipIt Agent Pack

Connect your AI agent to [ClipIt](https://clipit.dev) and let it do the work: import long videos, find the best moments, cut clips, add captions, generate thumbnails and B-Roll, render, export, and publish to your social accounts — all from a conversation with your agent.

This repo contains everything an agent needs to operate ClipIt: skill files, ready-to-run scripts, and setup instructions agents understand. **You read the next section; your agent reads the rest.**

## Connect Your Agent (the human part — 2 minutes)

1. **Get an API key**: go to [clipit.dev](https://clipit.dev) → **Settings** → **API Keys** → **Connect an Agent**. Pick your agent from the list — ClipIt generates a setup prompt tailored to it.
2. **Paste the setup prompt into your agent**, then give it the API key when it asks. (Treat the key like a password — your agent is instructed never to repeat it.)
3. **Done.** Ask your agent to "list my ClipIt videos" — if it answers, you're connected.

No setup prompt handy? Just tell your agent:

> Set up ClipIt for me using https://github.com/nplusm-Clippy/ClipIt-Agent-Pack — I'll give you my API key when you're ready to store it.

Your agent will take it from there.

## What Your Agent Can Do

- **Import** videos from YouTube, Vimeo, Twitch, or direct upload
- **Transcribe** with word-level timing and speaker labels
- **Find viral moments** automatically and suggest ready-to-cut clips
- **Create and edit clips** with precise start/end timing
- **Caption** with styled presets (bold, neon, minimal, classic, tiktok-viral) or custom fonts and colors
- **Generate thumbnails** from a text description, in up to 4K
- **Generate B-Roll** overlay images and video, including start/end frame transitions
- **Render and export** in the format, aspect ratio, and quality you need
- **Publish and schedule** to 13 social platforms (YouTube, TikTok, Instagram, Facebook, LinkedIn, X, Bluesky, Threads, Pinterest, Reddit, Telegram, Snapchat, Google Business)
- **Track performance** — post metrics, platform breakdowns, top clips
- **Watch your spend** — check credit balance and estimate costs before anything paid runs
- **Top up autonomously with approval** — discover direct x402, Stripe-managed x402, and Stripe Link MPP rails when credits run low

## Example Requests

Just talk to your agent in plain language:

> "Take this YouTube video, find the three funniest moments, render them for TikTok with neon captions, generate thumbnails, and post them to TikTok and Instagram"

> "Import this video and create a clip from 1:30 to 2:15 with the title 'Best moment'"

> "Check my credit balance and estimate the cost before rendering this 45-second clip"

> "Export clip_xyz as a 1080p MP4 in 9:16 and give me the download URL"

> "Post clip_xyz to TikTok and YouTube with the caption 'Best moment of 2026' and schedule it for tomorrow at 9am"

---

# For Agents

**Start with [`AGENTS.md`](AGENTS.md)** — it has the full setup, verification, and working rules. The sections below are framework-specific install paths.

## Install by Framework

### Claude Code

```bash
npm install -g @clipit-ai/cli
printf '%s' "$CLIPPER_API_KEY" | clipit auth set-key --stdin
clipit agent install claude        # writes ~/.claude/skills/clipit-cli/SKILL.md
clipit videos list                 # verify the account connection
```

Or clone this repo — Claude Code reads the root `CLAUDE.md` automatically and discovers every skill in `clipper/*/SKILL.md`.

### Codex

```bash
npm install -g @clipit-ai/cli
printf '%s' "$CLIPPER_API_KEY" | clipit auth set-key --stdin
clipit agent install codex         # writes ~/.codex/skills/clipit-cli/SKILL.md
clipit videos list                 # verify the account connection
```

Or clone this repo — Codex reads the root `AGENTS.md` automatically.

### Hermes

```bash
hermes skills tap add nplusm-Clippy/ClipIt-Agent-Pack

hermes skills install clipper/video-management clipper/clip-creation clipper/export-rendering clipper/thumbnail-generation clipper/caption-generation clipper/broll-generation clipper/social-publishing clipper/account-insights clipper/machine-payments
```

Add `CLIPPER_API_KEY` and `CLIPPER_BASE_URL=https://clipit.dev` to `~/.hermes/.env` or the equivalent environment file for that runtime.

### OpenClaw and Other CLI Agents

`clipit agent install` accepts ANY framework name; unknown names get the full generic instructions written under `~/.config/clipit/agent-skills/<name>/clipit-cli/`:

```bash
npm install -g @clipit-ai/cli
printf '%s' "$CLIPPER_API_KEY" | clipit auth set-key --stdin
clipit agent install openclaw      # or crewai, langchain, your-framework
clipit videos list                 # verify the account connection
```

Point your framework's skill loader at the generated `SKILL.md`, or clone this repo — frameworks that honor `AGENTS.md` pick it up automatically.

### Any Agent Using Raw REST

The Python scripts in `scripts/` are thin REST bindings (`pip install -r requirements.txt`, every script has `--help`). Fetch live, permission-scoped operating instructions:

```bash
python scripts/get_agent_instructions.py --target generic --format markdown
```

Or call `GET /api/v1/agent/instructions?target=<your-framework>&format=markdown` directly.

## Verify the Connection

```bash
python scripts/list_videos.py      # or: clipit videos list
```

Any successful response — even an empty list — means you're connected. A `401` means the key was entered incorrectly; re-copy it from ClipIt Settings. A `403` names the missing permission; enable it on the key in **Settings → API Keys**. With the CLI installed, `clipit doctor --json` reports connectivity, auth state, and the active profile in one shot.

## Skills

| Skill | What It Does | Key Scripts |
|-------|-------------|-------------|
| [video-management](clipper/video-management/SKILL.md) | Use enterprise library sources; import, upload, list, transcribe, and delete videos | `list_assets.py`, `use_library_video.py`, `transcribe_video.py` |
| [clip-creation](clipper/clip-creation/SKILL.md) | AI clip suggestions, create, edit, render, download | `suggest_clips.py`, `create_clip.py`, `render_clip.py` |
| [export-rendering](clipper/export-rendering/SKILL.md) | Export jobs and download URLs | `start_export.py`, `wait_for_export.py`, `download_export.py` |
| [thumbnail-generation](clipper/thumbnail-generation/SKILL.md) | AI thumbnails from text descriptions | `generate_thumbnail.py` |
| [caption-generation](clipper/caption-generation/SKILL.md) | Word-level captions with style presets | `generate_captions.py`, `update_captions.py` |
| [broll-generation](clipper/broll-generation/SKILL.md) | AI B-Roll image and video overlays | `plan_broll.py`, `generate_broll.py` |
| [social-publishing](clipper/social-publishing/SKILL.md) | Exact-artifact, exact-account posting/scheduling to 13 platforms | `list_social_accounts.py`, `post_to_social.py`, `schedule_social_post.py` |
| [account-insights](clipper/account-insights/SKILL.md) | Credits, cost estimates, analytics | `get_credits_balance.py`, `estimate_cost.py`, `get_top_clips.py` |
| [machine-payments](clipper/machine-payments/SKILL.md) | Approved x402 or Stripe Link MPP credit purchases | `get_payment_capabilities.py`, `get_billing_catalog.py`, `create_payment_attempt.py`, `get_payment_receipt.py` |

## Permissions

Each skill requires specific API key permissions. The **Connect an Agent** flow in ClipIt settings pre-selects the common ones.

| Capability | Required Permissions |
|------------|---------------------|
| video-management | `file_upload`, `url_extraction`, `video_processing`, `transcription` |
| clip-creation, export-rendering | `clip_generation` |
| thumbnail-generation | `thumbnail_generation` |
| caption-generation | `caption_generation` |
| broll-generation | `broll_generation` |
| social-publishing | `social_publishing`, `clip_generation` (exact delivery-state preflight) |
| account-insights | none — every key can read its own credits and analytics |
| machine-payments | none beyond an active API key; payment signing stays in the user's wallet or Link payer |
| asset uploads | `file_upload` |
| orchestration | `clippy_agent` |

## Exact Social Publishing

Publishing is fail-closed around both the finished clip and the destination account. The scripts first read the clip's canonical delivery-state, select one verified exact-current export, list currently connected or workspace-granted social accounts, and then pin all of that authority in the request. They send `exportId`, `expectedSnapshotId`, `expectedOutputObjectFingerprint`, `expectedAccountIds`, and `publishExactCurrentArtifact=true` automatically.

List the available account IDs immediately before publishing:

```bash
python scripts/list_social_accounts.py
```

Enterprise workspace keys publish or schedule one exact platform/account per request. The clip/export must also be a client-selected deliverable:

```bash
python scripts/post_to_social.py \
  --clip-id clip_xyz \
  --platform linkedin \
  --account-id account_linkedin_123 \
  --export-id export_xyz \
  --caption "Approved client caption" \
  --wait

python scripts/schedule_social_post.py \
  --clip-id clip_xyz \
  --platform twitter \
  --account-id account_x_456 \
  --caption "Approved client caption" \
  --scheduled-for "2030-08-20T14:00:00Z" \
  --wait
```

`--export-id` is optional when only one completed export exactly matches the current editor snapshot; use it to resolve an otherwise ambiguous delivery-state. Ordinary API keys retain comma-separated `--platforms` plus `--account-ids platform=id,...` support. Enterprise workspace publishing records usage for reporting but does not debit the client $CLIP balance; ordinary keys keep normal publishing charges and approval rules.

## Credits & Costs

Ordinary API keys consume [$CLIP credits](https://clipit.dev) at the same rates as the web app. Enterprise workspace keys record calculated usage for reporting without debiting the client account:

| Operation | Cost |
|-----------|------|
| Video transcription | 1 $CLIP per minute of audio |
| AI clip suggestions | ~5 $CLIP |
| Thumbnail generation | ~19.5 $CLIP |
| B-Roll image generation | ~9.1 $CLIP |
| B-Roll video generation (8s) | ~208 $CLIP (~416 with audio) |
| Social post | 65 $CLIP per platform |
| Clip render / export | Varies by duration and quality |

**Ordinary-key agents: always preflight paid operations** — check the balance and estimate first, and confirm with the user before spending. Enterprise workspace keys may still estimate for reporting, but they do not require client balance:

```bash
python scripts/get_credits_balance.py
python scripts/estimate_cost.py --operation-type lambda_render --provider aws_lambda --model-id remotion-4.0 videoSeconds=45
```

## Async Operations

Long-running operations return IDs that must be polled. Generic jobs use `wait_for_job.py`; **export jobs use the export endpoint, not the generic jobs endpoint**:

```bash
python scripts/wait_for_job.py --job-id job_abc123
python scripts/wait_for_export.py --job-id export_abc123
```

If a **webhook URL** is configured on the API key, ClipIt POSTs completion/failure events when supported jobs finish.

## API Documentation

- Interactive Swagger UI: **https://clipit.dev/api/v1/docs**
- OpenAPI 3.1 spec: **https://clipit.dev/api/v1/openapi.json**

## Support

- Issues: https://github.com/nplusm-Clippy/ClipIt-Agent-Pack/issues
- ClipIt: https://clipit.dev

## License

MIT
