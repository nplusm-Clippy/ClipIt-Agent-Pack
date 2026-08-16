---
name: clipper-clip-creation
description: Create, find, edit, render, and download video clips from ClipIt videos
version: 1.1.0
author: nplusm-Clippy
license: MIT
platforms: [macos, linux, windows]
metadata:
  tags: [Video, ClipIt, Clips, Render, AI, Viral, TikTok, YouTube Shorts]
  hermes:
    tags: [Video, ClipIt, Clips, Render, AI, Viral, TikTok, YouTube Shorts]
    requires_toolsets: [terminal]
required_environment_variables:
  - name: CLIPPER_API_KEY
    prompt: "Enter your ClipIt API key"
    help: "Get one at https://clipit.dev -> Settings -> API Keys -> Quick Connect"
    required_for: "ClipIt API access"
---

# ClipIt Clip Creation

## When to Use

Use this skill when the user wants to:
- Find viral moments in a video using AI
- Create clips manually with specific start/end times
- Edit clip timing, title, or caption
- Render a clip as a downloadable video (with captions, cropping, etc.)
- Download a rendered clip
- List or manage existing clips

**Prerequisite:** The video must be imported first (use the video-management skill). Transcription is required for captions and AI suggestions, but not for a manual no-caption clip.

**Cost preflight:** For AI suggestions and rendering, use the account-insights skill first: `get_credits_balance.py` to check balance, then `estimate_cost.py` when duration/model metrics are known.

## Quick Reference

| Operation | Script | Cost |
|-----------|--------|------|
| AI viral clip suggestions | `suggest_clips.py --video-id <id> [--count 5]` | ~5 $CLIP |
| Create clip manually | `create_clip.py --video-id <id> --start <s> --end <s>` | Minimal |
| List clips | `list_clips.py [--video-id <id>]` | Free |
| Get clip details | `get_clip.py --clip-id <id>` | Free |
| Update clip | `update_clip.py --clip-id <id> [--start] [--end] [--title] [--caption]` | Free |
| Delete clip | `delete_clip.py --clip-id <id>` | Free |
| Initialize enterprise snapshot | `initialize_editor_snapshot.py --workspace-id <id> --clip-id <id>` | Free |
| Render clip | `render_clip.py --clip-id <id> [--aspect-ratio 9:16] [--wait]` | Varies |
| Download rendered clip | `download_clip.py --clip-id <id>` | Free |

## Procedure

### Finding Viral Moments with AI

**When to use:** The user wants AI to find the best, most shareable moments in their video. This is the most common starting point.

**Prerequisites:** The video MUST be transcribed first. If not, use `transcribe_video.py --video-id <id> --wait` from the video-management skill.

**Steps:**
1. Run `python scripts/suggest_clips.py --video-id <id> --count 5`
2. The AI (Grok 4.20 with 2M context) analyzes the full transcript and returns clip opportunities
3. Each opportunity includes: `title`, `startTime`, `endTime`, `reason`, `confidence`, `themes`, `viralPotential`
4. To create a clip from a suggestion, use the `startTime` and `endTime` values with `create_clip.py`

**Options:**
- `--count N` — number of suggestions (1-20, default 5)
- `--platforms tiktok,youtube` — optimize suggestions for specific platforms
- `--min-duration 15` / `--max-duration 60` — constrain clip duration

**Example (full workflow):**
```bash
# 1. Suggest clips
python scripts/suggest_clips.py --video-id vid_abc123 --count 3 --platforms tiktok

# 2. Create clips from the top suggestions (using start/end from the results)
python scripts/create_clip.py --video-id vid_abc123 --start 45.2 --end 78.9 --title "Best moment"
python scripts/create_clip.py --video-id vid_abc123 --start 120.0 --end 155.5 --title "Funny reaction"
```

### Creating a Clip Manually

**When to use:** The user knows exactly which segment they want.

**Steps:**
1. Run `python scripts/create_clip.py --video-id <id> --start <seconds> --end <seconds>`
2. Optionally add `--title "My clip"` and `--caption "Caption text"`
3. The response includes the `clipId` for rendering

### Rendering a Clip

**When to use:** The user wants a downloadable video file. Rendering applies captions, aspect ratio, and quality settings.

**Steps:**
1. Check credits with `python scripts/get_credits_balance.py` from account-insights
2. Run `python scripts/render_clip.py --clip-id <id> --aspect-ratio 9:16 --quality high --wait`
3. Rendering uses AWS Lambda (Remotion) and typically takes 30-120 seconds
4. On completion, the job result includes the `renderUrl`
5. To get a fresh download URL: `python scripts/download_clip.py --clip-id <id>`

**Render options:**
- `--aspect-ratio` — `16:9` (YouTube), `9:16` (TikTok/Reels), `1:1` (Instagram), `4:5` (Facebook)
- `--quality` — `standard`, `high`, `4k`
- `--captions` / `--no-captions` — include caption overlay (default: yes)
- `--caption-style` — `bold`, `minimal`, `neon`, `classic`
- `--watermark` — add ClipIt watermark (default: no)
- `--auto-reframe` / `--no-auto-reframe` — enable or disable automatic subject framing
- `--workspace-id` and `--profile` — require an exact named enterprise workspace preflight before rendering

**Example:**
```bash
python scripts/render_clip.py --clip-id clip_xyz --aspect-ratio 9:16 --quality high --caption-style neon --wait
```

### Enterprise Canonical Clip Workflow

**When to use:** The ClipIt team is producing a clip from a contracted client's workspace with a workspace API key.

1. Activate one named profile for the workspace and verify its exact scope:
   ```bash
   clipit auth use "enterprise-client-slug"
   python scripts/verify_enterprise_workspace.py \
     --workspace-id "<expected-workspace-id>" \
     --profile "enterprise-client-slug"
   ```
2. List the client's workspace assets, register the chosen upload as a processing video, and confirm the video is visible in that same scope:
   ```bash
   python scripts/list_assets.py --type video
   python scripts/use_library_video.py --asset-id "<asset-id>"
   python scripts/list_videos.py
   ```
3. If captions or AI suggestions are desired, transcribe first. Skip this for a manual no-caption clip:
   ```bash
   python scripts/transcribe_video.py --video-id "<video-id>" --wait
   ```
4. Create the clip, then initialize its canonical editor snapshot. Caption intent is explicit; the safe no-caption default is shown:
   ```bash
   python scripts/create_clip.py \
     --video-id "<video-id>" \
     --start 0 \
     --end 30 \
     --title "Client-facing title"

   python scripts/initialize_editor_snapshot.py \
     --workspace-id "<expected-workspace-id>" \
     --profile "enterprise-client-slug" \
     --clip-id "<clip-id>" \
     --aspect-ratio 9:16 \
     --fit-background blur \
     --quality high \
     --no-captions \
     --caption-style minimal
   ```
5. Render with the same aspect ratio, quality, and caption choice. Keep automatic reframing off so the render does not replace the snapshot's full-frame authority:
   ```bash
   python scripts/render_clip.py \
     --workspace-id "<expected-workspace-id>" \
     --profile "enterprise-client-slug" \
     --clip-id "<clip-id>" \
     --aspect-ratio 9:16 \
     --quality high \
     --no-captions \
     --caption-style minimal \
     --no-auto-reframe \
     --wait
   ```
6. Export with matching framing, then use the export-rendering skill to deliver the completed export as `ready`:
   ```bash
   python scripts/start_export.py \
     --clip-id "<clip-id>" \
     --aspect-ratio 9:16 \
     --reframe-mode fit \
     --fit-background blur \
     --resolution 1080p \
     --wait
   ```

For captions, use `--captions --caption-style <style>` on **both** `initialize_editor_snapshot.py` and `render_clip.py`. If any aspect, quality, caption, or framing choice changes, initialize a new canonical snapshot intentionally before exporting. Delivery creates `ready` review state only; client selection remains client authority.

### Downloading a Rendered Clip

**When to use:** After rendering, to get the actual video file URL.

**Steps:**
1. Run `python scripts/download_clip.py --clip-id <id>`
2. Returns `{ downloadUrl, expiresAt }` — the URL is a signed S3 link valid for a limited time
3. If the clip hasn't been rendered, you'll get a 404 — render it first

## Pitfalls

- **Transcript required for AI suggestions.** `suggest_clips.py` will fail if the video isn't transcribed. Always transcribe first.
- **Rendering takes time.** Use `--wait` to block until done, or poll the returned `jobId`. Don't try to download before rendering completes.
- **Changing clip timing invalidates the render.** If you update start/end times with `update_clip.py`, the previous render is stale — re-render before downloading.
- **Download URLs expire.** Each call to `download_clip.py` generates a fresh signed URL. Don't cache them.
- **Credits vary by render duration and quality.** A 60-second 4K render costs more than a 15-second standard render. Use account-insights before bulk renders.
- **Enterprise settings must match the canonical snapshot.** Use the same aspect ratio, quality, and explicit caption choice for initialization and rendering, and use `--no-auto-reframe`. Reinitialize if those choices change.
- **A workspace ID is not enough by itself.** Enterprise initialization and rendering must pass the exact named-profile identity preflight; never fall back to a personal key.

## Verification

- **AI suggestions succeeded:** Response contains a non-empty `opportunities` array with `startTime`, `endTime`, `title` for each
- **Clip created:** Response includes a `clipId` (non-empty string) and status 201
- **Render succeeded:** Job status is `completed` and `result.renderUrl` is a valid URL
- **Enterprise snapshot pinned:** Initialization returns the requested `clipId`, an integer `editorVersion`, an `editorStateHash`, and the requested caption state
- **Download URL works:** The URL from `download_clip.py` returns a video file when fetched (Content-Type: video/mp4)
