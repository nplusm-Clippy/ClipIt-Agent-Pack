---
name: clipper-delivery-qa
description: Verify that ClipIt clips, timelines, generated media, audio mixes, exports, social packages, and blueprint workflows are actually ready before render, delivery, publishing, or a final done claim. Use for preflight QA, blocker classification, artifact inspection, or completion audits.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Quality Assurance, Delivery, Export, Publishing, Definition of Done]
  hermes:
    tags: [ClipIt, Quality Assurance, Delivery, Export, Publishing, Definition of Done]
    requires_toolsets: [terminal]
---

# ClipIt Delivery QA

Use with `clipit-operator`. Read:

- [delivery-checklist.md](references/delivery-checklist.md)
- [../clipit-operator/references/media-qa.md](../clipit-operator/references/media-qa.md)
- [../clipit-operator/references/time-and-state.md](../clipit-operator/references/time-and-state.md)

Load this skill whenever an agent is about to say an edit, package, export, publish workflow, or long-running job is complete.

## Operating loop

1. Resolve exact current clip/project/sequence/artifact IDs and the user's destination/definition of done.
2. Re-read current timeline, layers, render/export, and authority state after the last mutation.
3. Describe and call `runDeliveryReadinessQA` with explicit targets, aspect, duration/platform requirements, render requirement, and completion criteria.
4. For blueprint work, also call `runBlueprintExportQA`.
5. Inspect actual visual and audio artifacts; automated readiness output does not replace media inspection.
6. Classify each finding as fail, warning, not reviewed, or explicitly waived.
7. Fix and rerun QA on changed state, or stop with a precise blocker.

## Completion gate

- A fail blocks ready/export/publish/done claims.
- A warning remains visible and ships only under the user's acceptance policy.
- `not_reviewed` is never a pass.
- A waiver names one finding and one artifact/version; it does not apply after regeneration.
- Rendered does not mean exact-current, exported, delivered, client-selected, or published.
- Provider completed does not mean applied or QA-passed.

## Handoff

Report inspected evidence, artifact/version IDs, QA status, blockers/warnings/waivers, source-audio review, destination fit, and which next gate—render, export, client selection, or publish—still remains.
