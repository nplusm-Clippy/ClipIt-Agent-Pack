---
name: clipper-crop-reframing
description: Analyze subjects and protected visual context, then apply static, timed, automatic, fit/full-frame, or stacked-speaker reframing in ClipIt. Use for aspect-ratio conversion, speaker/product focus, face re-detection, crop layouts, or framing QA.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Crop, Reframe, Face Detection, Vertical Video, Layout]
  hermes:
    tags: [ClipIt, Crop, Reframe, Face Detection, Vertical Video, Layout]
    requires_toolsets: [terminal]
---

# ClipIt Crop and Reframing

Use with `clipit-operator`. Before changing framing, read:

- [reframing-workflow.md](references/reframing-workflow.md)
- [../clipit-operator/references/time-and-state.md](../clipit-operator/references/time-and-state.md)
- [../clipit-operator/references/media-qa.md](../clipit-operator/references/media-qa.md)

## Operating loop

1. Read the current clip/aspect and inspect important faces, products, slides, screens, graphics, and intentional full-frame moments.
2. Describe the live crop analysis and application tools.
3. Choose the least invasive strategy: fit/full-frame, one static focal point, timed layouts, automatic framing, or an explicit stacked-speaker preset.
4. If detection returns pixel coordinates, normalize them with actual source dimensions before any crop application.
5. Apply through one execution owner and preserve returned state/job IDs.
6. Re-read the current crop/layout state, preview transitions, and run framing QA across the whole clip.

## Tool family

Current discovery hints include:

- `autoFrameClip`
- `findCropTarget`
- `analyzeVisualContext`
- `explainVisualPlan`
- `setTimedCropLayouts`
- `redetectFaces`
- `applyStackedSpeakerReframe`
- crop/aspect application tools exposed by the clip skill

Use live descriptions for parameters and confirmation/cost behavior.

## Rules

- Query for concrete noun phrases and useful synonyms, not subjective adjectives.
- Protect on-screen information as well as faces; speaker-only crops can destroy demos, slides, or product context.
- Detection is evidence, not permission to crop. Resolve multiple plausible subjects against the brief.
- Use timed layouts or split at a motion/scene boundary when one static crop cannot follow the action safely.
- Preserve headroom, eyeline, hand/product interaction, captions, and graphic-safe areas.
- Do not call separate face detection or aspect/preset tools around an all-in-one stacked-speaker operation unless its live contract explicitly requires it.
- Changing framing invalidates downstream render/export QA.

## Completion

Do not call reframing complete from detection output. The saved crop/layout must be visible in current state and previewed at start, end, layout transitions, scene changes, and representative speaker/action moments.
