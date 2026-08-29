---
name: clipper-clip-creation
description: Discover moments and create, inspect, update, render, or download ClipIt clips while preserving source-time meaning and exact enterprise editor state. Use for manual or AI-assisted clip selection and saved-clip lifecycle work.
license: MIT
metadata:
  version: "2.0.0"
  tags: [Video, ClipIt, Clips, Render, AI, Viral, TikTok, YouTube Shorts]
  hermes:
    tags: [Video, ClipIt, Clips, Render, AI, Viral, TikTok, YouTube Shorts]
    requires_toolsets: [terminal]
---

# ClipIt Clip Creation

Use with `clipit-operator`. Prefer `clipit videos`, `clipit clips`, `clipit ask`, or discovered MCP tools; use these Python scripts for REST fallback and exact enterprise recipes. Read [../clipit-operator/references/editorial-workflow.md](../clipit-operator/references/editorial-workflow.md) before selecting or assembling moments.

## When to Use

Use this skill when the user wants to:
- Find viral moments in a video using AI
- Create clips manually with specific start/end times
- Edit clip timing, title, or caption
- Render a clip as a downloadable video (with captions, cropping, etc.)
- Download a rendered clip
- List or manage existing clips

**Prerequisite:** The video must be imported first (use the video-management skill). Transcription is required for captions and AI suggestions, but not for a manual no-caption clip.

**Spend preflight:** For AI suggestions and rendering, obtain a live estimate for the exact request and apply the user's approved cap. Enterprise usage-only keys report internal usage separately from the zero client charge.

## Quick Reference

| Operation | Preferred path | REST fallback |
|-----------|----------------|---------------|
| AI clip suggestions | `clipit videos suggest-clips <videoId> --count 5 --confirm --json` | `suggest_clips.py --video-id <id>` |
| Create/list/get/update/delete | `clipit clips ...` | matching clip scripts |
| Render and wait | `clipit clips render <clipId> --confirm --max-credits <cap> --json`; `clipit jobs wait <jobId>` | `render_clip.py --clip-id <id> --wait` |
| Initialize/exact enterprise delivery | enterprise Python recipe | `initialize_editor_snapshot.py`; `run_enterprise_exact_delivery.py` |

## Procedure

### Finding Viral Moments with AI

**When to use:** The user wants AI to find the best, most shareable moments in their video. This is the most common starting point.

**Prerequisites:** The video MUST be transcribed first. If not, use `transcribe_video.py --video-id <id> --wait` from the video-management skill.

**Steps:**
1. Run `python scripts/suggest_clips.py --video-id <id> --count 5`
2. ClipIt's current inference route analyzes the full transcript and returns clip opportunities; do not pin a remembered provider/model in the skill.
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

**When to use:** A personal-key user wants a downloadable video file. Enterprise workspace clips use the exact recipe below.

**Steps:**
1. Re-read current clip/editor state and run delivery QA for the intended artifact.
2. Preflight the exact render with a user-approved cap.
3. Run `clipit clips render <id> --aspect 9:16 --quality high --confirm --max-credits <cap> --json` or the fallback script.
4. Save the job ID and wait/resume with the matching generic job waiter.
5. Inspect the current rendered media, then obtain a fresh download URL only when needed.

**Render options:**
- `--aspect-ratio` — `16:9` (YouTube), `9:16` (TikTok/Reels), `1:1` (Instagram), `4:5` (Facebook)
- `--quality` — `standard`, `high`, `4k`
- `--captions` / `--no-captions` — include caption overlay (default: yes)
- `--caption-style` — `bold`, `minimal`, `neon`, `classic`
- `--watermark` — add ClipIt watermark (default: no)
- `--auto-reframe` / `--no-auto-reframe` — enable or disable automatic subject framing
- `--workspace-id` — rejects direct enterprise rendering and points to the exact-delivery recipe, preventing legacy caption-style overwrite

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
4. Create the clip, then initialize its canonical editor snapshot with the approved exact style. For an exact TikTok Viral request, place the full object (including scale, words-per-line, position, animation, and highlights) in `style.json`:
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
     --captions \
     --caption-style-json @style.json
   ```
5. Run the exact recipe with the version/hash/settings revision returned by initialization. The recipe preflights all capabilities and cost before approval, then resumes render/export/delivery from a durable checkpoint:
   ```bash
   python scripts/run_enterprise_exact_delivery.py \
     --workspace-id "<expected-workspace-id>" \
     --profile "enterprise-client-slug" \
     --clip-id "<clip-id>" \
     --style-json @style.json \
     --expected-editor-version "<initializer-editor-version>" \
     --expected-editor-state-hash "<initializer-editor-state-hash>" \
     --expected-clip-settings-revision "<initializer-settings-revision>" \
     --max-credits "<approved-cap>" \
     --no-outro \
     --confirm \
     --wait
   ```
6. Verify the final receipt has the approved `captionStyleHash`, outro policy, snapshot lineage, output fingerprint, artifact duration, and render/export/delivery IDs. Delivery creates `ready` review state only; client selection remains client authority.

Never use direct `render_clip.py --workspace-id ...` for enterprise work; its legacy four-style request can replace exact fields. If a requested field is unsupported, return one product-owned blocked state rather than asking the client to edit and save manually.

### Downloading a Rendered Clip

**When to use:** After rendering, to get the actual video file URL.

**Steps:**
1. Run `python scripts/download_clip.py --clip-id <id>`
2. Returns `{ downloadUrl, expiresAt }` — the URL is a signed S3 link valid for a limited time
3. If the clip hasn't been rendered, you'll get a 404 — render it first

## Pitfalls

- **Deletion needs explicit scope approval.** Re-read the target clip and describe what is removed before `clipit clips delete <id> --confirm` or the REST fallback.
- **Transcript required for AI suggestions.** `suggest_clips.py` will fail if the video isn't transcribed. Always transcribe first.
- **Rendering takes time.** Use `--wait` to block until done, or poll the returned `jobId`. Don't try to download before rendering completes.
- **Changing clip timing invalidates the render.** If you update start/end times with `update_clip.py`, the previous render is stale — re-render before downloading.
- **Download URLs expire.** Each call to `download_clip.py` generates a fresh signed URL. Don't cache them.
- **Do not use remembered costs.** Preflight the current render duration, quality, profile, and provider route before approval.
- **Enterprise exactness is acceptance, not best effort.** The normalized caption object/hash, snapshot identity, source binding, outro policy, and final duration must all match before delivery.
- **A workspace ID is not enough by itself.** Enterprise initialization and the exact recipe must pass the named-profile identity preflight; never fall back to a personal key.

## Verification

- **AI suggestions succeeded:** Response contains a non-empty `opportunities` array with `startTime`, `endTime`, `title` for each
- **Clip created:** Response includes a `clipId` (non-empty string) and status 201
- **Render succeeded:** Job status is `completed` and `result.renderUrl` is a valid URL
- **Enterprise snapshot pinned:** Initialization returns the requested `clipId`, an integer `editorVersion`, an `editorStateHash`, and the requested caption state
- **Enterprise receipt complete:** Exact recipe returns `state: "completed"` with render/export/delivery IDs and verified caption, snapshot, output-fingerprint, outro, and duration lineage
- **Download URL works:** The URL from `download_clip.py` returns a video file when fetched (Content-Type: video/mp4)
