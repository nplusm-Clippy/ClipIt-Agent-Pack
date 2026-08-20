---
name: clipper-caption-generation
description: Generate and style word-level captions for ClipIt clips
version: 1.0.0
author: nplusm-Clippy
license: MIT
platforms: [macos, linux, windows]
metadata:
  tags: [Video, ClipIt, Captions, Subtitles, Styling, Typography]
  hermes:
    tags: [Video, ClipIt, Captions, Subtitles, Styling, Typography]
    requires_toolsets: [terminal]
required_environment_variables:
  - name: CLIPPER_API_KEY
    prompt: "Enter your ClipIt API key"
    help: "Get one at https://clipit.dev -> Settings -> API Keys -> Quick Connect"
    required_for: "ClipIt API access"
---

# ClipIt Caption Generation

## When to Use

Use this skill when the user wants to:
- Add captions/subtitles to a clip
- Change caption styling (font, color, size, position, preset)
- Apply a specific caption look (bold, neon, minimal, TikTok-viral)

**Prerequisite:** The parent video must be transcribed first (use the video-management skill). Captions are derived from the transcript's word-level timing.

## Quick Reference

| Operation | Script | Cost |
|-----------|--------|------|
| Generate captions | `generate_captions.py --clip-id <id> [--preset bold]` | Minimal |
| Update caption style | `update_captions.py --clip-id <id> [--preset neon]` | Free |
| Set exact enterprise style | `set_caption_style.py --workspace-id <id> --clip-id <id> --profile <name> (--style-json @style.json | --directive "caption size 200% single") --expected-editor-version <n> --expected-editor-state-hash <hash> --expected-clip-settings-revision <n>` | Free |

## Procedure

### Generating Captions for a Clip

**When to use:** The user has a clip and wants captions added.

**Prerequisites:** The parent video MUST be transcribed. If not, captions will fail with a `TRANSCRIPT_REQUIRED` error.

**Steps:**
1. Run `python scripts/generate_captions.py --clip-id <id>`
2. Optionally apply a preset: `--preset bold` (or `minimal`, `neon`, `classic`, `tiktok-viral`)
3. The response includes the caption segments (start/end times + text) and the applied style
4. Captions are stored on the clip — they'll appear in the next render

**Style options (all optional):**
- `--preset` — `bold` | `minimal` | `neon` | `classic` | `tiktok-viral`
- `--font` — `Inter` | `Arial` | `Bangers` | `Oswald` | `Roboto`
- `--font-size` — 12 to 120 (default 48)
- `--color` — hex color like `"#FFFFFF"`
- `--position` — `top` | `center` | `bottom` (default bottom)

If a preset is provided, its settings override individual style options.

**Example:**
```bash
python scripts/generate_captions.py --clip-id clip_xyz --preset tiktok-viral
```

### Updating Caption Style

**When to use:** The user already has captions but wants to change the look.

**Steps:**
1. Run `python scripts/update_captions.py --clip-id <id> --preset neon`
2. You can change individual properties: `--font Bangers --font-size 60 --color "#00FF00"`
3. The update is partial — only the provided fields change, the rest stay

**Example:**
```bash
python scripts/update_captions.py --clip-id clip_xyz --color "#FF0000" --font-size 72 --position center
```

### Re-rendering After Caption Changes

After changing captions, the clip needs to be re-rendered for the changes to appear in the video file. Use the clip-creation skill:

```bash
python scripts/render_clip.py --clip-id <id> --captions --wait
```

### Exact Enterprise Caption Style

For a workspace clip, never approximate a requested style with one of the four legacy names. Initialize with `--caption-style-json @style.json`, or use `set_caption_style.py` with the exact version/hash/settings revision returned by initialization. A TikTok Viral request with 2x scale can be expressed as:

```json
{
  "presetId": "tiktok-viral",
  "fontSizeScale": 2,
  "wordsPerLine": 2,
  "captionLineMode": "single-line",
  "position": "bottom",
  "animation": "pop"
}
```

For the bounded shorthand `caption size N% auto|single|stacked`, pass the user's phrase unchanged through `--directive`. ClipIt converts `N%` to `fontSizeScale: N / 100`; `single` or `single line` means `captionLineMode: "single-line"`. It does not mean one word per caption and must not change `wordsPerLine`. For example:

```bash
python scripts/set_caption_style.py \
  --workspace-id <workspace-id> \
  --clip-id <clip-id> \
  --profile <profile> \
  --directive "caption size 200% single" \
  --expected-editor-version <version> \
  --expected-editor-state-hash <hash> \
  --expected-clip-settings-revision <revision>
```

Only percentages from 50% through 300% and the three documented line layouts are accepted. Extra or ambiguous text fails closed. The directive patches the current canonical style, preserving the preset, font, color, position, animation, and words-per-caption setting.

The directive response replaces the initializer handoff. Do not reuse the initialization identity after `set_caption_style.py` succeeds. Copy its full normalized `captionStyle` into the style JSON for exact delivery, retain its `captionStyleHash`, and replace all three pinned values with the response's new `editorVersion`, `editorStateHash`, and `clipSettingsRevision`:

```bash
python scripts/run_enterprise_exact_delivery.py \
  --workspace-id <workspace-id> \
  --clip-id <clip-id> \
  --profile <profile> \
  --style-json @set-caption-response-style.json \
  --expected-editor-version <set-caption-response-editor-version> \
  --expected-editor-state-hash <set-caption-response-editor-state-hash> \
  --expected-clip-settings-revision <set-caption-response-settings-revision> \
  --max-credits <approved-cap> \
  --no-outro
```

The read-only plan's `exactCaptionStyle.styleHash` must equal the retained mutation `captionStyleHash`. Only then rerun with `--confirm`, keeping the same mutation identity, normalized style, usage cap, and outro policy. If the recipe returns `processing`, keep that same original request and use the plan/receipt hash and resume fields; never fall back to the initialization identity.

The mutation must return the normalized `captionStyle`, a 64-character `captionStyleHash`, strict capability metadata, and `renderQueued: false`. Compare every requested field before approval. Then use `run_enterprise_exact_delivery.py`; direct captioned `render_clip.py --workspace-id ...` is blocked because the legacy render endpoint can replace the exact style.

## Pitfalls

- **Transcript required.** If you get `TRANSCRIPT_REQUIRED`, transcribe the video first using `transcribe_video.py`.
- **Changes don't appear in existing renders.** After updating captions, re-render the clip to bake in the new styling.
- **Presets override individual style options.** If you set `--preset bold` and `--font Arial`, the preset's font wins. Apply the preset first, then override specific fields with `update_captions.py`.
- **Single is a line layout.** For exact enterprise styling, map `Single` to `captionLineMode: "single-line"`; never change `wordsPerLine` unless the user separately requests a different words-per-caption value.
- **Do not hand editor repair to the client.** If the exact enterprise schema rejects a requested field, report one product-owned blocked capability state. Do not ask the CEO to open the editor, save, or reply when the automation cannot prove the exact style.

## Verification

- **Captions generated:** Response contains a non-empty `segments` array with `startTime`, `endTime`, `text` for each segment
- **Style applied:** Response `style` object matches what was requested (font, size, color, position)
- **Exact enterprise style applied:** Normalized `captionStyle` matches every approved field and `captionStyleHash` is retained through the recipe receipt, export, and deliverable verification
- **Visible in render:** After re-rendering with `--captions`, the video file shows caption text at the correct timestamps
