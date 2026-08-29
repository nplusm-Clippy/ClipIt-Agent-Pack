# Blueprint Execution

## Tool map

Current discovery hints:

- `analyzeEditingBlueprint`: parse segments, timecodes, asset refs, overlays, transitions, pacing, short-form candidates, rough assembly, and gaps.
- `createBlueprintExecutionPlan`: build `rough_assembly`, `guided_full_edit`, or `full_service` passes.
- `resolveBlueprintAssets`: map B-Roll, gold moments, standing rules, linked docs, templates, logos, and SFX to authorized assets.
- `planBlueprintGraphics`: structure lower thirds, title/chapter cards, pull quotes, tip cards, diagrams, and end cards.
- `planBlueprintEffects`: structure cuts, speed changes, transitions, pattern interrupts, SFX, silence, and fades.
- `auditBlueprintRolloutReadiness`: classify guided versus full-service blockers.
- `applyTextOverlayToClip`: apply supported text overlays to a saved clip.
- `applyTimelineEffectPrimitive`: persist supported effects on an owned timeline placement.
- `createBlueprintJobState`, `updateBlueprintJobState`, `getBlueprintJobState`: durable checkpoint/resume state.
- `runBlueprintExportQA`: blueprint-specific render/duration/aspect/overlay/B-Roll checks.

Always use the live descriptions for fields and supported enums.

## Parse and normalize

Capture:

```text
Blueprint/source identity:
Segments and subsegments:
Source-time ranges:
Final/sequence-time targets:
Required quotes and exact visible text:
Source assets and unresolved labels:
Graphics and templates:
Effects/transitions/pattern interrupts:
Audio/SFX/music instructions:
Platform/aspect/duration requirements:
Short-form candidates:
Standing rules:
Capability gaps and ambiguities:
```

Do not “fix” contradictory timecodes silently. Surface the conflict and choose only with evidence or user direction.

## Service levels

- `rough_assembly`: prepare and place source-timecode clip batches only.
- `guided_full_edit`: create pass-by-pass execution with human checkpoints.
- `full_service`: include assets, graphics, B-Roll, audio polish, QA, and export readiness, while retaining every required approval and capability gate.

The selected label does not waive missing assets, paid confirmation, media QA, or delivery authority.

## Pass order

1. Resolve source and assets.
2. Build rough assembly from source timecodes.
3. Verify story order and retained words.
4. Apply cleanup cuts and pacing.
5. Lock destination aspect and framing.
6. Add approved B-Roll/Alter.
7. Apply supported graphics/overlays.
8. Apply effects/pattern interrupts after the cut is stable.
9. Polish source/generated audio and SFX.
10. Run blueprint export QA and delivery QA.
11. Render/export current state and create requested derivatives.

## Durable job state

Create job state before the first mutation. Each update should include current step, status/progress, exact artifact IDs/versions, observation, blocker, approval state, and next action. Do not store secrets or signed URLs.

On resume:

1. Load job state.
2. Read current project/sequence/timeline and affected media layers.
3. Compare current IDs/state with the checkpoint.
4. Mark drift explicitly.
5. Continue the first incomplete safe pass; never replay completed mutations blindly.

## Graphics and effects

Use text overlays for supported text-only lower thirds, pull quotes, generic overlays, and simple tip cards. Exact visible text must come from the blueprint or approved content. Full visual cards/diagrams requiring templates remain blocked until assets/capability exist.

Use effect primitives only on live timeline placement IDs and in the time domain the described tool expects. Preserve the exact blueprint instruction as provenance. An instruction saved on a timeline is not visual QA proof.

## Final reconciliation

Re-read the original blueprint and produce a coverage ledger:

```text
item/reference -> executed artifact/evidence | blocked reason | explicit defer/waiver
```

Every instruction must land in one category. Then run both blueprint-specific export QA and destination delivery QA on the current artifact.
