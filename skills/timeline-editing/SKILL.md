---
name: clipper-timeline-editing
description: Inspect and edit ClipIt timelines by adding saved clips, moving, trimming, splitting, layering, or removing placements while preserving time-domain and track integrity. Use for sequence assembly, pacing, cut changes, track routing, collision handling, or any request to change what appears when on a timeline.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Timeline, Video Editing, Trim, Split, Sequence]
  hermes:
    tags: [ClipIt, Timeline, Video Editing, Trim, Split, Sequence]
    requires_toolsets: [terminal]
---

# ClipIt Timeline Editing

This is a generated standalone bundle. Resolve shell commands and `scripts/` paths from this installed skill directory, or use absolute paths to its bundled scripts; a repository checkout is not required. Python fallbacks use [requirements.txt](requirements.txt). Install those dependencies in your chosen Python environment before running a fallback. The ClipIt CLI and MCP remain the preferred transports.

Use with `clipit-operator`. Before the first mutation, read:

- [references/timeline-operations.md](references/timeline-operations.md)
- [references/clipit-operator--time-and-state.md](references/clipit-operator--time-and-state.md)
- [references/clipit-operator--editorial-workflow.md](references/clipit-operator--editorial-workflow.md)

## Operating loop

1. Confirm the active project and sequence. Do not infer them from a video or saved clip ID.
2. Discover the live timeline tools and describe the selected tool.
3. Call `getTimelineContents` before editing and retain timeline clip IDs, track IDs, placements, durations, and source bounds.
4. Name the time domain and intended editorial delta.
5. Submit one bounded operation through one execution owner.
6. Call `getTimelineContents` again and verify the delta, adjacent edits, track routing, gaps, collisions, and resulting duration.

## Tool family

The current server commonly exposes:

- `getTimelineContents`
- `addExistingClipToTimeline`
- `removeClipFromTimeline`
- `trimClip`
- `moveClip`
- `splitClip`

Treat these names as discovery hints, not schemas. Use `clipit tools describe <functionName> --json` or the MCP `tools/list` result immediately before execution.

## Editorial rules

- Build A-roll and story rhythm before decoration.
- Use the timeline placement ID returned by the timeline read for move, trim, split, or remove—not the library clip ID unless the live schema explicitly says so.
- Place cuts on thought, breath, emotion, or motion boundaries. Preserve the speaker's meaning.
- Check neighboring audio and picture at every boundary.
- Decide whether a trim should leave a gap, ripple, or require an explicit move; never assume implicit ripple behavior.
- For a multi-item edit, checkpoint after each logical pass so failures do not leave an unknown partial state.

## Approval and completion

Timeline edits can be user-visible mutations even when unmetered. Use the confirmation behavior reported by the live tool/CLI and obtain approval when the requested edit is ambiguous, destructive, or removes material. A successful mutation response is not completion until the current timeline read and preview/QA prove the intended result.

## Bundled Support Files

Generated from canonical Agent Pack sources; do not edit these copies.

- [references/LICENSE](references/LICENSE)
- [references/clipit-operator--editorial-workflow.md](references/clipit-operator--editorial-workflow.md)
- [references/clipit-operator--media-prompting.md](references/clipit-operator--media-prompting.md)
- [references/clipit-operator--time-and-state.md](references/clipit-operator--time-and-state.md)
- [references/timeline-operations.md](references/timeline-operations.md)
- [requirements.txt](requirements.txt)
- [references/bundle-manifest.json](references/bundle-manifest.json)
