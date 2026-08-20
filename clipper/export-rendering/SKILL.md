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
| Run exact enterprise delivery | `run_enterprise_exact_delivery.py --workspace-id <id> --clip-id <id> --profile <name> --style-json @style.json --max-credits <n> --confirm` | Varies |
| Deliver eligible enterprise export | `deliver_export.py --workspace-id <id> --export-id <id> --profile <name>` | Free |
| List enterprise deliveries | `list_deliverables.py --workspace-id <id> --profile <name> [--status ready\|selected]` | Free |

## Procedure

### Starting an Export

**When to use:** The user wants a finished media file with specific export settings.

**Steps:**
1. Use account-insights first. Ordinary keys may check balance; enterprise usage-only keys must use the balance-free preflight.
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

For enterprise work, create the canonical snapshot and then use the idempotent exact-delivery recipe. The recipe performs a complete preflight before approval, verifies the exact caption hash, reuses or queues the current render, starts one snapshot-bound export, and creates one exact-lineage ready deliverable. Starting from the active named workspace profile:

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
  --captions \
  --caption-style-json @style.json
python scripts/run_enterprise_exact_delivery.py \
  --workspace-id "<expected-workspace-id>" \
  --profile "enterprise-client-slug" \
  --clip-id "<clip-id>" \
  --style-json @style.json \
  --expected-editor-version "<initializer-editor-version>" \
  --expected-editor-state-hash "<initializer-editor-state-hash>" \
  --expected-clip-settings-revision "<initializer-settings-revision>" \
  --max-credits 15 \
  --no-outro \
  --confirm \
  --wait
python scripts/list_deliverables.py \
  --workspace-id "<expected-workspace-id>" \
  --profile "enterprise-client-slug" \
  --export-id "<recipe-export-id>" \
  --status ready
```

The first recipe call always returns a plan before provider work. `--confirm` advances only that plan hash and exact clip/snapshot lineage. If processing is incomplete, rerun with the same original request fields plus `--resume-token`, `--plan-hash`, `--caption-style-hash`, and `--expected-final-duration` from the receipt lineage; completed stages are not repeated. `--no-outro` is required when the approved artifact duration must equal the canonical content duration. Direct captioned enterprise `render_clip.py` calls are blocked because the legacy endpoint can replace exact caption fields; the deliberate no-caption path remains available. Delivery stops at `ready`; only the client can select it for publishing.

**Common options:**
- `--format` — `mp4`, `mov`, `avi`, `webm`, `mkv`
- `--aspect-ratio` — `original`, `16:9`, `9:16`, `1:1`, `4:3`, `4:5`, `2:3`
- `--resolution` — `2160p`, `1080p`, `720p`, `480p`, `360p`, `original`
- `--bitrate`, `--framerate`, `--codec`, `--quality-preset` — quality settings
- `--include-audio` / `--no-audio` — include or omit audio
- `--include-outro` / `--no-outro` — explicitly approve the four-second branded outro or exact content duration
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
     --profile "enterprise-client-slug"
   ```
4. The script verifies `/api/v1/agent/me`, reads the completed export, and sends its enterprise execution, snapshot version/hash, caption-style hash, output fingerprint, outro policy, and probed artifact duration as exact expectations. ClipIt derives the title and note from the bound canonical snapshot; callers cannot supply contradictory copy.
5. If the same export was already delivered, the script safely lists that exact export and returns it with `replayed: true`; it does not create a duplicate or downgrade an existing client selection.
6. Check review state with:
   ```bash
   python scripts/list_deliverables.py \
     --workspace-id "<expected-workspace-id>" \
     --profile "enterprise-client-slug" \
     --export-id "<completed-export-id>"
   ```

`ready` means the clip is visible for client review. `selected` means the client explicitly granted publishing authority through the enterprise portal. Agents cannot select or unselect deliverables.

## Error Handling

- **402 insufficient credits / spend limit.** Stop and use account-insights. For enterprise usage-only keys report internal usage separately from the zero client charge; do not request owner balance access.
- **409 premature download.** The export is not completed yet. Run `wait_for_export.py` and retry download after completion.
- **404 export not found.** Check the `exportJobId` and that it belongs to the same API key owner.
- **409 editor identity conflict.** Rerun `start_export.py` so it refreshes delivery-state; never hand-build editor pins.
- **403 enterprise workspace preflight.** Stop and select the exact named workspace profile. Do not fall back to a personal key.
- **409 DELIVERY_EXISTS.** `deliver_export.py` resolves the existing exact delivery automatically and reports `replayed: true`.
- **Exact-style capability blocked.** Report the rejected field as a product-owned capability gap. Do not ask the client to open or save the editor.
- **Failed export.** Inspect the error returned by `wait_for_export.py`; source media issues may require re-rendering or choosing different export settings.

## Verification

- **Export started:** Response includes `exportJobId`, `status`, and `pollUrl`
- **Export completed:** `wait_for_export.py` returns `status: "completed"`
- **Download URL available:** `download_export.py` returns `downloadUrl`
- **Correct poller used:** Export jobs are never polled with `wait_for_job.py`
- **Editor identity pinned:** Export start output includes `snapshotId`, `expectedEditorVersion`, `expectedEditorStateHash`, and `idempotencyKey`
- **Recipe receipt complete:** Receipt contains `state: "completed"`, exact `captionStyleHash`, `includeOutro`, render/export/delivery IDs, snapshot lineage, output fingerprint, and artifact duration
- **Delivery ready:** `deliver_export.py` returns one exact-workspace deliverable with `status: "ready"`, or an existing `ready`/`selected` delivery with `replayed: true`
- **Client authority preserved:** Only the enterprise portal changes a delivery from `ready` to `selected`
