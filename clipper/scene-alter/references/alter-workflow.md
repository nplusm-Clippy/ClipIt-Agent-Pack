# Selected-Section Alter Workflow

## Selection gate

Prefer the editor's selected-block context. Otherwise require one explicit bounded range in the time domain accepted by the live schema. The current Alter contract supports short selected blocks and static supported output aspects; describe the tool to confirm exact duration/aspect constraints before planning.

If timed or multi-subject reframing makes the selected input unsupported, do not silently flatten it. Explain the conflict and choose a supported current state only with the user's direction.

## Analyze

Use `analyzeAlterSelection` to capture:

- source/clip/timeline time interpretation;
- selected first and last frames;
- duration/aspect/mode constraints;
- existing overlapping Alter layers;
- identity, objects, action, camera, and lighting to preserve.

If the user asks for several transformations, split them into independent ranges/generations.

## Plan

`planVideoAlter` is read-only. The plan should prove:

- the exact selected range;
- one requested visual delta;
- preservation instruction ending “Keep everything else the same.”;
- standard/pro mode and current capabilities;
- whether the result should be applied;
- overlap replacement behavior;
- source-audio preservation;
- current estimate and approval cap.

Do not regenerate merely to see the cost. Use the plan.

## Generate and resume

Submit the exact approved plan fields once. Record the generation ID. Poll `getVideoAlterStatus`; do not create a second generation after a timeout or unchanged status until the first is proved failed/nonexistent.

## Inspect before apply

At matching timestamps, compare source/output for:

- requested change;
- each real person's identity, anatomy, age appearance, skin tone, hair, clothing, eyeline, and action;
- camera, framing, timing, lighting, objects, text/logos, and background elements that were not targeted;
- temporal flicker, morphing, discontinuity, or new subjects;
- first/last-frame continuity into surrounding source;
- unchanged source audio.

Fail if more than the requested delta changes materially.

## Apply, adjust, revert

Use one reversible Alter replacement layer. Default to replacing overlapping attempts. After application, inspect layer ID, start, duration, enabled state, fades, and `preserveOriginalAudio` in current state.

Use `updateVideoAlterLayer` for supported free timing/enabled/fade/mix adjustments. These do not repair a visually bad generation. Use `revertVideoAlter` to restore the original section, then verify the layer is absent/disabled and original picture/audio are current.

## Handoff state

```text
clip and selected range:
plan identity and approved cap:
generation ID/status:
QA status/findings:
layer ID/application state:
source audio verified:
current render/export stale or refreshed:
```
