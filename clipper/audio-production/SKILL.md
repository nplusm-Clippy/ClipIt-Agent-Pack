---
name: clipper-audio-production
description: Analyze, generate, apply, and mix ClipIt audio including source dialogue, Gemini Flash TTS voiceovers, MiniMax Music 2.6 beds, uploaded layers, normalization, EQ, dynamics, fades, loops, and ducking. Use for narration, music, sound layers, voice clarity, or final-mix work.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Audio, Voiceover, TTS, Music, Mixing, MiniMax Music]
  hermes:
    tags: [ClipIt, Audio, Voiceover, TTS, Music, Mixing, MiniMax Music]
    requires_toolsets: [terminal]
---

# ClipIt Audio Production

Use with `clipit-operator`. Before paid generation or final mixing, read:

- [audio-workflow.md](references/audio-workflow.md)
- [../clipit-operator/references/media-prompting.md](../clipit-operator/references/media-prompting.md)
- [../clipit-operator/references/media-qa.md](../clipit-operator/references/media-qa.md)
- [../clipit-operator/references/time-and-state.md](../clipit-operator/references/time-and-state.md)

## Operating loop

1. Resolve the target clip and run `analyzeAudioMix` before changing layers or processing unless the user supplied exact current-state settings.
2. Decide whether the task is source-audio control, cleanup/preset, existing-layer placement, paid voiceover, or paid music.
3. For TTS, keep literal text separate from performance direction. For music, keep style separate from lyrics and mix controls.
4. Call `planVoiceover` or `planMusicBed`, inspect duration/fields/estimate, and present a capped approval.
5. Generate once with exact approved fields; save the generation ID and resume via `getAudioGenerationStatus`.
6. Apply or update one explicit audio layer and re-read the mix.
7. Listen to the final mixed artifact for words, sync, intelligibility, clipping, seams, fades, and source-audio behavior.

## Tool family

Current discovery hints include:

- `analyzeAudioMix`
- `planVoiceover`, `generateVoiceover`
- `planMusicBed`, `generateMusicBed`
- `updateSourceAudio`
- `applyAudioLayer`, `updateAudioLayer`
- `applyAudioPreset`
- `getAudioGenerationStatus`

Describe each live schema before mutation.

## Rules

- Source audio remains authoritative unless the user explicitly asks to mute, lower, replace, or process it.
- “Generate” does not imply “apply” unless the requested outcome is an edit on the clip; represent that choice explicitly.
- Do not imitate a living or private person's voice.
- Default a dialogue music bed to instrumental, restrained, loopable, and ducked; verify rather than relying on a remembered numeric level.
- Processing presets are starting points. Analyze and listen after applying them.
- A visually generated B-Roll or Alter asset never authorizes provider audio replacement.

## Completion

Report generation/layer IDs, exact script or music intent, placement/mix settings, source-audio state, and listening QA. A generated file without correct timeline application and final-mix inspection is not a finished audio edit.
