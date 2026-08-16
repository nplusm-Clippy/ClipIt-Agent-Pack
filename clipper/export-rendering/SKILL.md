---
name: clipper-export-rendering
description: Start, wait for, download, and deliver ClipIt exports
version: 1.1.0
author: nplusm-Clippy
license: MIT
platforms: [macos, linux, windows]
metadata:
  tags: [Video, ClipIt, Export, Render, Download, Remotion]
  hermes:
    tags: [Video, ClipIt, Export, Render, Download, Remotion]
    requires_toolsets: [terminal]
required_environment_variables:
  - name: CLIPPER_API_KEY
    prompt: "Enter your ClipIt API key"
    help: "Get one at https://clipit.dev -> Settings -> API Keys -> Connect an Agent"
    required_for: "ClipIt API access"
---

# ClipIt Export Rendering

## When to Use

Use this skill when the user wants to:
- Export a clip as a downloadable media file
- Choose export format, aspect ratio, resolution, bitrate, codec, or audio options
- Poll a running export job
- Get a fresh signed download URL for a completed export
- Place a completed workspace export in an enterprise client's Delivered Clips tab
- Check whether the client has selected a delivered clip for publishing

Exports are separate from generic jobs. Always poll export jobs with `GET /api/v1/exports/{jobId}` via `wait_for_export.py`, not `wait_for_job.py`.

## Quick Reference

| Operation | Script | Cost |
|-----------|--------|------|
| Start export | `start_export.py --clip-id <id> [--start 0] [--end 30] [--format mp4]` | Varies |
| Wait for export | `wait_for_export.py --job-id <exportJobId>` | Free |
| Download export | `download_export.py --job-id <exportJobId>` | Free |
| Deliver enterprise export | `deliver_export.py --workspace-id <id> --export-id <id> --title <title>` | Free |
| List enterprise deliveries | `list_deliverables.py --workspace-id <id> [--status ready\|selected]` | Free |

## Procedure

### Starting an Export

**When to use:** The user wants a finished media file with specific export settings.

**Steps:**
1. Use account-insights first: `python scripts/get_credits_balance.py`
2. When duration is known, estimate render/export cost:
   ```bash
   python scripts/estimate_cost.py \
     --operation-type lambda_render \
     --provider aws_lambda \
     --model-id remotion-4.0 \
     videoSeconds=30
   ```
3. Run `python scripts/start_export.py --clip-id <id> --start 0 --end 30 --format mp4 --aspect-ratio 9:16 --wait`
4. If you omit `--wait`, save the returned `exportJobId`

`start_export.py` first reads `/api/v1/clips/{clipId}/delivery-state` and refuses to export unless ClipIt returns a verified `current_editor_snapshot`. It pins `expectedEditorVersion` and `expectedEditorStateHash` from that response and generates a new idempotency key for a new export. The script prints that non-secret key before sending the export request. If the outcome is unknown, retry the exact same export with that key via `--idempotency-key`; do not reuse it for a different export.

For enterprise work, create the canonical snapshot before rendering/exporting. Starting from the active named workspace profile, the exact sequence is:

```bash
python scripts/verify_enterprise_workspace.py \
  --workspace-id "<expected-workspace-id>" \
  --profile "enterprise-client-slug"
python scripts/list_assets.py --type video
python scripts/use_library_video.py --asset-id "<asset-id>"
python scripts/list_videos.py

# Required for captions or AI suggestions; omit for a manual no-caption clip.
python scripts/transcribe_video.py --video-id "<video-id>" --wait

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
python scripts/start_export.py \
  --clip-id "<clip-id>" \
  --aspect-ratio 9:16 \
  --reframe-mode fit \
  --fit-background blur \
  --resolution 1080p \
  --wait
python scripts/deliver_export.py \
  --workspace-id "<expected-workspace-id>" \
  --export-id "<completed-export-id>" \
  --title "Client-facing title"
python scripts/list_deliverables.py \
  --workspace-id "<expected-workspace-id>" \
  --export-id "<completed-export-id>" \
  --status ready
```

If captions are desired, transcribe and pass the same `--captions --caption-style <style>` choice to snapshot initialization and rendering. Do not change aspect, quality, caption, or framing settings between those steps. Delivery stops at `ready`; only the client can select the deliverable for publishing, after which the agent may verify it with `list_deliverables.py --status selected`.

**Common options:**
- `--format` — `mp4`, `mov`, `avi`, `webm`, `mkv`
- `--aspect-ratio` — `original`, `16:9`, `9:16`, `1:1`, `4:3`, `4:5`, `2:3`
- `--resolution` — `2160p`, `1080p`, `720p`, `480p`, `360p`, `original`
- `--bitrate`, `--framerate`, `--codec`, `--quality-preset` — quality settings
- `--include-audio` / `--no-audio` — include or omit audio
- `--options-json` — pass advanced exportStart schema fields as a JSON object
- `--idempotency-key` — reuse only for an exact retry after an unknown outcome

### Waiting for an Export

**When to use:** `start_export.py` returned an `exportJobId` and the export is still pending or processing.

**Steps:**
1. Run `python scripts/wait_for_export.py --job-id <exportJobId>`
2. The script polls `/api/v1/exports/{jobId}` until status is `completed`, `failed`, or `cancelled`
3. On success, the result includes export metadata and output details

### Downloading an Export

**When to use:** Export status is `completed` and the user needs a fresh signed URL.

**Steps:**
1. Run `python scripts/download_export.py --job-id <exportJobId>`
2. Use the returned `downloadUrl` before it expires
3. If the URL expires, run the script again for a fresh one

### Delivering an Enterprise Export

**When to use:** A workspace export is completed and ready for the client to review.

1. Keep the workspace's named non-default profile active.
2. Copy the exact workspace ID from the ClipIt admin dashboard.
3. Run:
   ```bash
   python scripts/deliver_export.py \
     --workspace-id "<expected-workspace-id>" \
     --export-id "<completed-export-id>" \
     --title "Client-facing title" \
     --note "Optional review note"
   ```
4. The script verifies `/api/v1/agent/me` against that workspace before mutation and creates a `ready` deliverable only. It never selects publishing authority for the client.
5. If the same export was already delivered, the script safely lists that exact export and returns it with `replayed: true`; it does not create a duplicate or downgrade an existing client selection.
6. Check review state with:
   ```bash
   python scripts/list_deliverables.py \
     --workspace-id "<expected-workspace-id>" \
     --export-id "<completed-export-id>"
   ```

`ready` means the clip is visible for client review. `selected` means the client explicitly granted publishing authority through the enterprise portal. Agents cannot select or unselect deliverables.

## Error Handling

- **402 insufficient credits / spend limit.** Stop and use account-insights. The user needs more $CLIP or a higher API-key spend limit.
- **409 premature download.** The export is not completed yet. Run `wait_for_export.py` and retry download after completion.
- **404 export not found.** Check the `exportJobId` and that it belongs to the same API key owner.
- **409 editor identity conflict.** Rerun `start_export.py` so it refreshes delivery-state; never hand-build editor pins.
- **403 enterprise workspace preflight.** Stop and select the exact named workspace profile. Do not fall back to a personal key.
- **409 DELIVERY_EXISTS.** `deliver_export.py` resolves the existing exact delivery automatically and reports `replayed: true`.
- **Failed export.** Inspect the error returned by `wait_for_export.py`; source media issues may require re-rendering or choosing different export settings.

## Verification

- **Export started:** Response includes `exportJobId`, `status`, and `pollUrl`
- **Export completed:** `wait_for_export.py` returns `status: "completed"`
- **Download URL available:** `download_export.py` returns `downloadUrl`
- **Correct poller used:** Export jobs are never polled with `wait_for_job.py`
- **Editor identity pinned:** Export start output includes `snapshotId`, `expectedEditorVersion`, `expectedEditorStateHash`, and `idempotencyKey`
- **Delivery ready:** `deliver_export.py` returns one exact-workspace deliverable with `status: "ready"`, or an existing `ready`/`selected` delivery with `replayed: true`
- **Client authority preserved:** Only the enterprise portal changes a delivery from `ready` to `selected`
