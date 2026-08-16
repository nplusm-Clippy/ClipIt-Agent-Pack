---
name: clipper-video-management
description: Use enterprise library sources, upload, import, list, delete, and transcribe videos in ClipIt
version: 1.3.0
author: nplusm-Clippy
license: MIT
platforms: [macos, linux, windows]
metadata:
  tags: [Video, ClipIt, Upload, Import, Transcription, YouTube, Vimeo]
  hermes:
    tags: [Video, ClipIt, Upload, Import, Transcription, YouTube, Vimeo]
    requires_toolsets: [terminal]
required_environment_variables:
  - name: CLIPPER_API_KEY
    prompt: "Enter your ClipIt API key"
    help: "Get one at https://clipit.dev -> Settings -> API Keys -> Quick Connect"
    required_for: "ClipIt API access"
  - name: CLIPPER_BASE_URL
    prompt: "Enter the ClipIt base URL (default: https://clipit.dev)"
    default: "https://clipit.dev"
    required_for: "Routing API requests"
---

# ClipIt Video Management

## When to Use

Use this skill when the user wants to:
- Import a video from a URL (YouTube, Vimeo, Twitch, or any supported platform)
- Upload a local video file to their ClipIt library
- Upload an image, video, audio, or raw file as a reusable library asset
- Use a client-uploaded enterprise library video as the source for clipping
- List or browse videos in their library
- Transcribe a video (word-level timestamps and speaker identification)
- Fetch an existing transcript
- Delete a video

This skill is typically the **first step** before using clip-creation, thumbnail-generation, or other ClipIt skills. Most workflows start here.

## Quick Reference

| Operation | Script | Permissions Needed |
|-----------|--------|--------------------|
| Import from URL | `import_video_from_url.py --url <url> [--wait]` | `url_extraction` |
| Upload local file | `upload_video.py --file <path> [--wait]` | `file_upload` |
| Upload library asset | `upload_asset.py --file <path> [--content-type <mime>]` | `file_upload` |
| Verify enterprise workspace | `verify_enterprise_workspace.py --workspace-id <id>` | Active team workspace key |
| List client library assets | `list_assets.py --type video` | `file_upload` |
| Use client library video | `use_library_video.py --asset-id <id>` | `file_upload`, `video_processing` |
| List videos | `list_videos.py [--limit N] [--offset N]` | `video_processing` |
| Get video details | `get_video.py --video-id <id>` | `video_processing` |
| Delete video | `delete_video.py --video-id <id>` | `video_processing` |
| Start transcription | `transcribe_video.py --video-id <id> [--wait]` | `transcription` |
| Fetch transcript | `get_transcript.py --video-id <id>` | `transcription` |

## Procedure

### Enterprise Workspace Guardrail (ClipIt Team Only)

Enterprise workspace keys are for the ClipIt team operating contracted client workspaces. Normal users and client users do not receive or configure these keys. Store every admin-created workspace key in a distinct non-default ClipIt CLI profile; never save one as the shared Hermes `CLIPPER_API_KEY`:

```bash
clipit auth set-key --stdin --profile "enterprise-client-slug"
clipit auth use "enterprise-client-slug"
```

Before reading or changing client content, select the named profile and verify it against the workspace ID shown in the admin dashboard:

```bash
python scripts/verify_enterprise_workspace.py \
  --workspace-id "<expected-workspace-id>"
```

Continue only when the response has `"verified": true` for the expected workspace. The preflight requires an active workspace, `team_operator` authority, and `enterprise_usage_only` billing. Keep that profile active for the client session and rerun the preflight whenever switching workspaces. Use an explicit `CLIPIT_PROFILE` for one-command isolation when needed. A successful `list_videos.py` response is not proof that the key belongs to the intended workspace.

### Importing a Video from URL

**When to use:** The user provides a YouTube, Vimeo, Twitch, or other video URL they want to work with.

**Steps:**
1. Run `python scripts/import_video_from_url.py --url "<url>" --wait`
2. The script returns the completed job JSON with `result.videoId`
3. Save the `videoId` — you'll need it for transcription and clip creation

**Important notes:**
- YouTube imports use a residential proxy and can take 30-120 seconds depending on video length
- Age-restricted, region-locked, or live stream URLs will fail — the error explains why
- The `--wait` flag polls until complete. Without it, you get a `jobId` to poll manually with `wait_for_job.py`

**Example:**
```bash
python scripts/import_video_from_url.py --url "https://youtube.com/watch?v=dQw4w9WgXcQ" --wait
```

### Uploading a Local Video File

**When to use:** The user has a video file on their machine.

**Steps:**
1. Run `python scripts/upload_video.py --file /path/to/video.mp4 --wait`
2. The completed job contains `result.videoId`, `result.durationSeconds`, and `result.audioHealth`
3. If `audioHealth` is `silent` or `no_audio`, warn the user — transcription will produce empty results

**Example:**
```bash
python scripts/upload_video.py --file ~/Videos/interview.mp4 --wait
```

### Uploading a Reusable Library Asset

**When to use:** An authorized operator needs to add an image, audio file, video, or raw brand asset directly through the API. Enterprise client footage should normally arrive through the client portal and be reused with `list_assets.py` plus `use_library_video.py`.

```bash
python scripts/upload_asset.py \
  --file /path/to/brand-logo.png \
  --content-type image/png
```

The script reserves a durable upload intent with a generated idempotency key, prints that non-secret key before the request, PUTs the exact declared bytes to the signed storage URL using the returned headers, then finalizes only with the returned `uploadIntentId`. It never treats a caller-provided object path, file size, or duration as storage authority. If the request outcome is unknown, reuse the same `--idempotency-key` only for the exact same file and metadata.

### Listing Videos

**When to use:** The user asks "what videos do I have?" or you need to find a video ID.

**Steps:**
1. Run `python scripts/list_videos.py`
2. Results are paginated — use `--limit` and `--offset` for large libraries
3. Each video shows: `id`, `title`, `durationSeconds`, `processingStatus`, `audioHealth`

### Using a Client-Uploaded Enterprise Library Video

**When to use:** The client has already uploaded raw footage through their Enterprise Source Library and the workspace API key should process it without uploading the bytes again.

**Steps:**
1. Complete the named-profile enterprise identity preflight above for the exact expected workspace
2. Run `python scripts/list_assets.py --type video` with the verified workspace profile active
3. Select the intended finalized asset by name and copy its `id`
4. Run `python scripts/use_library_video.py --asset-id <asset-id>`
5. Save the returned `videoId`
6. Use that `videoId` with `get_video.py`, `transcribe_video.py`, and the clip-creation scripts while keeping the same profile active

This operation is idempotent: retrying the same asset returns the same `videoId`. It reuses the existing source object and storage record, starts no transcription by itself, and does not debit client credits. Subsequent enterprise processing records metered usage without debiting the client.

### Transcribing a Video

**When to use:** Before using the clip-creation skill's `suggest_clips.py` (AI needs a transcript to find moments), or when the user asks for a transcript.

**Steps:**
1. First check if a transcript already exists: `python scripts/get_transcript.py --video-id <id>`
   - If it returns data, the transcript already exists — skip to next step
   - If it returns 404, proceed to transcribe
2. Trigger transcription: `python scripts/transcribe_video.py --video-id <id> --wait`
3. Transcription uses Deepgram Nova-3 and typically takes 10-60 seconds depending on video length
4. The transcript includes word-level timestamps and speaker diarization (when multiple speakers are detected)

**Cost:** Ordinary accounts spend 1 $CLIP per minute of audio. Enterprise workspace keys record the same measured usage without debiting the client.

### Deleting a Video

**When to use:** The user wants to remove a video and all its associated clips.

**Steps:**
1. Run `python scripts/delete_video.py --video-id <id>`
2. This cascades — all clips, thumbnails, and renders associated with the video are also deleted
3. For an Enterprise Source Library video, the processing video is removed but the client's original library asset is retained and can be registered again
4. This action is permanent for the deleted processing work and cannot be undone

## Pitfalls

- **Don't forget to wait for processing.** Video imports return a `jobId` — you MUST wait for completion before transcribing or creating clips. Use `--wait` or poll with `wait_for_job.py`.
- **Always transcribe before suggesting clips.** The `suggest_clips.py` script (in the clip-creation skill) requires a transcript to analyze. If no transcript exists, it will fail.
- **Don't re-transcribe** a video that already has a transcript — the API returns the existing one without re-running Deepgram, saving credits.
- **Don't upload client footage again.** For Enterprise Source Library footage, list assets and run `use_library_video.py`; the returned `videoId` is the normal processing identity.
- **Don't bypass durable asset finalization.** Keep the sign response's `intentId` and finalize through `upload_asset.py`; never invent an object path or file-size completion payload.
- **Don't trust a successful personal-library response as enterprise proof.** Match the named profile to the expected workspace with `verify_enterprise_workspace.py` before every client session.
- **Don't delete a source asset while its processing video is active.** Delete the processing video first; ClipIt retains the original enterprise library asset until the asset itself is explicitly deleted.
- **YouTube imports can fail** for age-restricted, region-locked, or live stream videos. Check the error message in the job result.
- **Large file uploads** (>2GB) may timeout. For very large videos, consider uploading to YouTube first and importing via URL.

## Verification

- **Import succeeded:** `job.status === "completed"` and `job.result.videoId` is a non-empty string
- **Transcription succeeded:** `get_transcript.py` returns 200 with a non-empty `segments` array
- **Video is ready for clipping:** it has BOTH a completed import AND a transcript
- **Enterprise identity is correct:** `verify_enterprise_workspace.py` returns `"verified": true` for the expected workspace ID before any client-content request
- **Enterprise library source is registered:** `use_library_video.py` returns a non-empty `videoId`; a retry returns the same ID
- **Library asset upload is finalized:** `upload_asset.py` returns the finalized asset after the exact intent-bound PUT
- **Delete succeeded:** `delete_video.py` prints confirmation and the video no longer appears in `list_videos.py`
