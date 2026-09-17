---
name: clipper-scene-alter
description: Plan, generate, inspect, apply, adjust, or revert a selected-section visual Alter in ClipIt using the current Gemini Omni Flash edit pipeline while preserving real-person identity, timing, framing, and source audio. Use when changing what happens inside a bounded video section.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Scene Alter, Video Edit, Gemini Omni Flash, Generative Video]
  hermes:
    tags: [ClipIt, Scene Alter, Video Edit, Gemini Omni Flash, Generative Video]
    requires_toolsets: [terminal]
---

# ClipIt Scene Alter

This is a generated standalone bundle. Resolve shell commands and `scripts/` paths from this installed skill directory, or use absolute paths to its bundled scripts; a repository checkout is not required. Python fallbacks use [requirements.txt](requirements.txt). Install those dependencies in your chosen Python environment before running a fallback. The ClipIt CLI and MCP remain the preferred transports.

Use with `clipit-operator`. Before planning, read:

- [references/alter-workflow.md](references/alter-workflow.md)
- [references/clipit-operator--media-prompting.md](references/clipit-operator--media-prompting.md)
- [references/clipit-operator--media-qa.md](references/clipit-operator--media-qa.md)
- [references/clipit-operator--time-and-state.md](references/clipit-operator--time-and-state.md)

## Operating loop

1. Resolve one valid selected block or explicit clip-local range; inspect current Alter layers.
2. Reduce the request to one coherent visual delta and name preservation invariants.
3. Describe and call `planVideoAlter`; inspect normalized range, model instruction, capability limits, and live estimate.
4. Present exact range, mode, application behavior, source-audio policy, and capped estimate for approval.
5. Call `generateVideoAlter` once with the approved fields and confirmation.
6. Save the generation ID and use `getVideoAlterStatus` to wait/resume.
7. Compare source and result at matching timestamps before applying.
8. If requested, apply one reversible replacement layer; re-read it and run timeline/audio/delivery QA.

## Tool family

Current discovery hints include:

- `analyzeAlterSelection`
- `planVideoAlter`
- `generateVideoAlter`
- `getVideoAlterStatus`
- `applyVideoAlter`
- `updateVideoAlterLayer`
- `revertVideoAlter`

Describe live schemas before execution.

## Non-negotiables

- One visual change per generation.
- Real-person identity, body, clothing, action, timing, camera, framing, and untouched scene elements remain source-authoritative.
- End the generation instruction with “Keep everything else the same.”
- Do not request or accept provider audio as authoritative. Preserve the original clip audio.
- Default to replacing overlapping Alter attempts instead of stacking them.
- Revert a bad layer rather than obscuring it with compensating generations.
- Provider success is not application or QA success.

## Completion

Report the selected range, generation/layer IDs, applied/reverted state, matching-timestamp QA, and source-audio verification. A queued or generated-but-unapplied Alter is not an edited clip.

## Bundled Support Files

Generated from canonical Agent Pack sources; do not edit these copies.

- [references/LICENSE](references/LICENSE)
- [references/alter-workflow.md](references/alter-workflow.md)
- [references/clipit-operator--media-prompting.md](references/clipit-operator--media-prompting.md)
- [references/clipit-operator--media-qa.md](references/clipit-operator--media-qa.md)
- [references/clipit-operator--time-and-state.md](references/clipit-operator--time-and-state.md)
- [requirements.txt](requirements.txt)
- [references/bundle-manifest.json](references/bundle-manifest.json)
