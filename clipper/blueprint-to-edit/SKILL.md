---
name: clipper-blueprint-to-edit
description: Parse a detailed editing blueprint, EDL-style brief, rundown, or multi-pass plan into a resumable ClipIt execution plan with asset resolution, rough assembly, graphics/effects passes, approvals, checkpoints, and export QA. Use when a long edit specification must become actual work without losing instructions.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Editing Blueprint, EDL, Workflow, Rough Assembly, QA]
  hermes:
    tags: [ClipIt, Editing Blueprint, EDL, Workflow, Rough Assembly, QA]
    requires_toolsets: [terminal]
---

# ClipIt Blueprint-to-Edit

Use with `clipit-operator`. Before execution, read:

- [blueprint-execution.md](references/blueprint-execution.md)
- [../clipit-operator/references/editorial-workflow.md](../clipit-operator/references/editorial-workflow.md)
- [../clipit-operator/references/time-and-state.md](../clipit-operator/references/time-and-state.md)
- [../clipit-operator/references/media-qa.md](../clipit-operator/references/media-qa.md)

## Core rule

Never treat a long blueprint as one free-form generation prompt. Parse it, expose ambiguities/capability gaps, resolve assets, create a pass plan, persist job state, and execute through checkpoints.

## Operating loop

1. Call `analyzeEditingBlueprint` first and retain parsed segments, timecodes, references, overlays, effects, short-form candidates, rough-assembly items, and gaps.
2. Call `resolveBlueprintAssets` before paid generation or full-service execution.
3. Call `createBlueprintExecutionPlan` with the requested service level.
4. Present executable passes, missing assets/capabilities, paid checkpoints, and definition of done.
5. Before timeline mutation, call `createBlueprintJobState`.
6. Execute one pass at a time through the appropriate domain skill; update job state after each checkpoint.
7. On resume, call `getBlueprintJobState` and reconcile current project/timeline state before continuing.
8. Run `runBlueprintExportQA` plus normal delivery QA before handoff.

## Tool family

Current discovery hints include analysis/plan tools, asset/graphics/effects planners, text/effect application primitives, persistent blueprint job state, rollout audit, and export QA. The complete list is in [blueprint-execution.md](references/blueprint-execution.md); describe live schemas before calls.

## Rules

- Source timecodes, final/sequence timecodes, and placement-local effect times must remain distinct.
- Asset labels and linked documents are references until resolved to authorized current assets.
- Do not fabricate logos, SFX, templates, brand rules, quotes, or footage to fill gaps.
- Paid B-Roll, image, Alter, voiceover, or music work keeps its own plan/approval/cap/QA gate.
- Store exact source blueprint instructions with applied primitives when supported.
- Report unsupported work as a product capability gap, not as silently completed prose.

## Completion

Report checkpoint state, artifacts/IDs, executed versus planned passes, missing/blocked items, QA status, and exact next step. A parsed plan or rough assembly is not a full edit.
