---
name: clipper-broll-generation
description: Plan, generate, inspect, and apply ClipIt B-Roll overlays using the current GPT Image 2 still and MiniMax H3 Max image-to-video pipeline. Use for story-relevant cutaways, visual proof, pacing resets, or start/end-frame transitions.
license: MIT
metadata:
  version: "2.0.0"
  tags: [Video, ClipIt, B-Roll, AI Video, GPT Image 2, H3 Max, Overlay]
  hermes:
    tags: [Video, ClipIt, B-Roll, AI Video, GPT Image 2, H3 Max, Overlay]
    requires_toolsets: [terminal]
---

# ClipIt B-Roll Generation

Use with `clipit-operator`. Before generation, read [../clipit-operator/references/media-prompting.md](../clipit-operator/references/media-prompting.md) and [../clipit-operator/references/media-qa.md](../clipit-operator/references/media-qa.md). Prefer `clipit broll` or discovered MCP tools; use the Python scripts as REST fallbacks.

## When to Use

Use this skill when the user wants to:
- Add a story-relevant visual cutaway or overlay to a clip
- Plan multiple B-Roll concepts for a clip before committing to generation
- Create transition effects between scenes using start/end frame interpolation

B-Roll is generated in two stages:
1. **Still generation** (GPT Image 2) creates the source frame or compatible start/end frames.
2. **Image-to-video** (MiniMax H3 Max on fal) animates the approved frame intent.

ClipIt mutes generated provider audio; the source clip audio remains authoritative. Always plan first, use the live estimate and an approved spend cap, then generate only selected concepts.

## Quick Reference

| Operation | Preferred path | REST fallback |
|-----------|----------------|---------------|
| Plan concepts | `clipit broll plan <clipId> --count 3 --confirm --json` | `plan_broll.py --clip-id <id> --count 3` |
| Generate B-Roll | `clipit broll generate <clipId> --concept-index <n> --confirm --max-credits <cap> --json` | `generate_broll.py --clip-id <id> --start <s> --end <s>` |
| Wait/resume | `clipit jobs wait <jobId> --stream` | `wait_for_job.py --job-id <id>` |

## Procedure

### Planning B-Roll Concepts

**When to use:** The user wants B-Roll ideas or an applied cutaway. Planning grounds the visual in transcript context and does not authorize generation.

**Steps:**
1. Read the target clip/transcript and identify the spoken moment and editorial purpose.
2. Run `clipit broll plan <clipId> --count 3 --confirm --json` or the fallback script.
3. Present each concept with its purpose, clip-local placement, still intent, and motion intent.
4. Select one concept, describe the live generate schema, preflight its exact cost, and obtain approval under a cap.

**Example:**
```bash
python scripts/plan_broll.py --clip-id clip_xyz --count 3 --theme "technology" --wait
```

### Generating B-Roll (Single Image Mode)

**When to use:** One source frame can support a coherent continuation such as a detail, atmosphere shot, controlled reveal, or simple action.

**Steps:**
1. Structure the still intent and motion intent separately for review. Prefer a planned concept; when using the REST `promptOverride`, provide the concise creative outcome and let ClipIt compile the provider-specific still and motion prompts.
2. Run `python scripts/generate_broll.py --clip-id <id> --start 10 --end 16 --prompt "..." --duration 6 --resolution 768p --image-quality high --wait`.
3. Treat `--start` and `--end` as clip-local placement and ensure the placement duration does not exceed generated duration.
4. Save the job/result IDs, inspect the actual still and sampled video frames, and confirm application to the intended range.

### Generating B-Roll (Start/End Frame Mode)

**When to use:** When the B-Roll needs a clear visual transformation — sunrise to sunset, empty room to filled room, cause and effect. Creates more intentional, controlled motion.

**Steps:**
1. Run with `--mode start_end_frame` and REQUIRED `--end-frame-description`:
   ```bash
   python scripts/generate_broll.py --clip-id clip_xyz --start 10 --end 18 \
     --prompt "empty conference room, morning light, clean modern design" \
     --mode start_end_frame \
     --end-frame-description "same conference room now filled with people, active meeting, warm afternoon light" \
     --transition-description "smooth time-lapse transition from empty to full" \
     --duration 8 --wait
   ```
2. ClipIt creates compatible GPT Image 2 start/end frames and H3 Max animates one continuous transformation.
3. Describe a physically plausible transition; do not use this mode for an unrelated cut.
4. Inspect both endpoint fidelity and temporal continuity before applying.

### Generation Options

- `--mode` — `single_image` (default) or `start_end_frame`
- `--duration` — current REST contract accepts 5-15 seconds; use the shortest duration that communicates the beat
- `--resolution` — `480p` or `768p`
- `--image-quality` — `low`, `medium`, `high`, or `auto`
- `--concept-index` — use a concept from `plan_broll.py` output (skips `--prompt`)
- `--prompt` — custom visual description (overrides planned concepts)

Never provide a remembered cost table. Use the plan/preflight returned for the current mode, duration, resolution, image quality, account, and provider route.

## Pitfalls

- **Planning is not approval.** Present the live estimate and cap before generation.
- **Resume the same job.** Use the returned `jobId`; unchanged progress alone is not failure.
- **`start_end_frame` mode requires `--end-frame-description`.** Without it, the script will fail.
- **Prompt motion, not the still.** H3 Max already receives the source frame; use one camera idea and one plausible action.
- **Protect real people.** Name identity/clothing/body/action invariants and use restrained motion.
- **No generated audio direction.** ClipIt preserves the source clip audio.
- **Re-render after adding B-Roll.** The B-Roll overlay is applied during the next clip render. Use `render_clip.py` after generating B-Roll.

## Verification

- **Plan succeeded:** Response contains a non-empty `concepts` array with `description`, `imagePrompt`, `videoPrompt` for each
- **Generation captured:** Job status is completed and current state references the generated still/video asset
- **Media QA passed:** Identity, anatomy, motion, continuity, crop, and prompt intent were inspected
- **B-Roll visible in render:** The current render shows it at the exact clip-local start/end while source audio remains correct
- **Start/end frame mode:** The video shows a clear visual transformation from start to end state
