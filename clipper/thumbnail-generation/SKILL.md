---
name: clipper-thumbnail-generation
description: Plan, generate, inspect, and attach ClipIt thumbnails through the current GPT Image 2 create/edit pipeline. Use for clip-based or standalone thumbnails, exact short visible text, brand/reference composition, and destination crop-safe image work.
license: MIT
metadata:
  version: "2.0.0"
  tags: [Video, ClipIt, Thumbnail, AI, Image Generation, GPT Image 2]
  hermes:
    tags: [Video, ClipIt, Thumbnail, AI, Image Generation, GPT Image 2]
    requires_toolsets: [terminal]
---

# ClipIt Thumbnail Generation

Use with `clipit-operator`. Before generation, read [../clipit-operator/references/media-prompting.md](../clipit-operator/references/media-prompting.md) and [../clipit-operator/references/media-qa.md](../clipit-operator/references/media-qa.md). Prefer `clipit thumbnails` or discovered MCP tools; use `generate_thumbnail.py` as the REST fallback.

## When to Use

Use this skill when the user wants to:
- Generate an AI thumbnail for a clip (enhances a frame from the clip)
- Generate a standalone thumbnail from a text prompt
- Get a specific style, mood, or text overlay on their thumbnail

ClipIt currently routes thumbnail create/edit work through GPT Image 2. With a clip ID, the current thumbnail can remain an authoritative edit reference; without one, the request is a create operation. Plan/preflight every generation and use the live estimate rather than a remembered price.

## Quick Reference

| Operation | Preferred path | REST fallback |
|-----------|----------------|---------------|
| Generate for clip | `clipit thumbnails generate --clip-id <id> --prompt "..." --confirm --max-credits <cap> --json` | `generate_thumbnail.py --clip-id <id> --prompt "..."` |
| Generate standalone | discovered `createImage`/thumbnail tool | `generate_thumbnail.py --prompt "..."` |
| Wait/resume | `clipit jobs wait <jobId> --stream` | `wait_for_job.py --job-id <id>` |

## Procedure

### Generating a Thumbnail for a Clip

**When to use:** The user has a clip and wants a scroll-stopping thumbnail.

**Steps:**
1. Read the clip, creator style when relevant, current thumbnail, destination aspect, and crop-safe needs.
2. Choose create or edit mode. If the current thumbnail/frame owns identity or composition, keep `useExistingThumbnail` enabled and state one requested delta plus invariants.
3. Write the GPT Image 2 prompt in the shared provider order; map every reference to one role.
4. Describe the live tool, preflight, set an approved cap, and generate once.
5. Save the job/thumbnail IDs, inspect the actual image, and confirm it is linked to the intended clip when requested.

**Prompt rules:**
- Name intended use and create/edit/composite mode.
- Put the single primary request first; map references by identity/product/style role.
- Describe one focal hierarchy and destination crop-safe placement.
- Put required visible text in exact quotes with placement and contrast.
- For a real person/product/logo edit, list identity and layout invariants explicitly.
- Keep resolution and quality in API fields; do not replace them with “high quality” prose.

**Example:**
```bash
python scripts/generate_thumbnail.py \
  --clip-id clip_xyz \
  --prompt 'Intended use: 16:9 YouTube thumbnail.
Mode: edit the supplied clip frame.
Primary request: intensify the genuine reaction with dramatic rim lighting and a bold red-and-white editorial treatment.
Invariants: preserve the same person, facial identity, expression anatomy, clothing, and source-camera perspective.
Composition: face on the left third; clean negative space on the right; keep all critical content inside crop-safe margins.
Exact visible text: "INSANE PLAY" in large high-contrast type on the right, spelled and capitalized exactly.
Avoid: identity drift, extra people, altered hands or teeth, duplicate text, logos, watermarks, and clutter.' \
  --aspect-ratio 16:9 \
  --resolution 4K \
  --quality high \
  --use-existing-thumbnail \
  --wait
```

### Generating a Standalone Thumbnail

**When to use:** The user wants a thumbnail image that isn't based on an existing clip frame.

**Steps:**
1. Run `python scripts/generate_thumbnail.py --prompt "description" --no-use-existing-thumbnail --wait` without `--clip-id`.
2. Make the subject/scene/composition self-contained; do not imply a missing reference.
3. Inspect and retain the returned image/thumbnail identity.

## Pitfalls

- **No remembered prices.** Use the current plan/preflight for aspect, resolution, quality, and account.
- **Aspect ratio matters.** YouTube thumbnails should be `16:9`, TikTok profile images `1:1`. Default is `16:9`.
- **Exact text needs inspection.** Keep it short, quote it verbatim, and reject spelling/casing/layout drift.
- **Preserve identity.** A provider success does not prove a referenced real person, product, or logo stayed accurate.
- **Resume, do not duplicate.** Query the returned job before starting a replacement after timeout.

## Verification

- **Generation captured:** Job status is completed and the returned asset can be opened
- **Image QA passed:** Requested delta, identity/product/logo, exact text, anatomy, composition, crop, and invariants were inspected
- **Thumbnail linked to clip:** The clip's `thumbnailUrl` field is updated (check with `get_clip.py`)
- **Image is correct size:** The URL returns an image matching the requested aspect ratio
