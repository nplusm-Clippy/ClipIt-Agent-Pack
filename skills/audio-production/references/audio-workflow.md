# Audio Production Workflow

## Diagnose before treatment

`analyzeAudioMix` should establish source-audio volume/mute state, existing layers, timing, fades, looping/ducking, and processing. Listen when an artifact is available. Separate problems:

- source recording noise or rumble;
- low or inconsistent dialogue level;
- harshness/mud;
- dynamics/clipping;
- generated layer placement;
- music masking speech;
- sync or edit-boundary discontinuity.

Use the narrowest treatment. Do not stack presets to chase an undefined “better.”

## Voiceover

1. Fit the literal script to the available duration.
2. Put only spoken words in `text`.
3. Put voice qualities, context, pace, emotion, emphasis, pauses, pronunciation, and restraints in `prompt`.
4. Select an allowlisted voice and matching language code from live capabilities.
5. Plan, inspect estimate, and confirm under a cap.
6. Check exact words, pronunciation, pacing, naturalness, and duration.
7. Apply at an explicit clip-local start and decide whether source audio stays, ducks, lowers, or mutes.

Do not use prompt directions that can be accidentally spoken. Do not rescue an overlong script by extreme speed instructions.

## Music bed

1. Decide instrumental versus lyrical; default to instrumental under dialogue.
2. Describe use/form, tempo, genre, mood, instrumentation, groove, production, and energy curve.
3. Put lyrics only in the lyrics field with section tags.
4. Put volume, placement, loop, fades, and ducking only in mix controls.
5. Plan, confirm, generate, inspect the musical result, then apply.

Avoid a long intro for short-form work, distracting lead melody under speech, unrequested vocals, abrupt drops, and a loop seam inside an exposed pause.

## Existing/uploaded layer

Use `applyAudioLayer` with an authoritative asset or generation ID. State kind, clip-local start, replace/add behavior, and mix settings. Re-read the returned layer ID before further updates.

## Source audio and processing

Use `updateSourceAudio` only for explicit source volume/mute intent. Use `applyAudioPreset` for a focused cleanup objective such as dialogue clarity or rumble removal. Describe the live preset options and avoid inventing EQ/dynamics values without evidence.

After processing, compare before/after for intelligibility, noise, pumping, tonal balance, and peak distortion. Normalization does not repair clipping or a bad edit.

## Mix order

1. Source dialogue and edits.
2. Corrective processing.
3. Voiceover/narration.
4. Music and supporting layers.
5. Ducking and automation.
6. Fades and boundary cleanup.
7. Whole-program listening and delivery QA.

Use solo only for diagnosis; clear it before final output. Check both headphones and a speech-focused low-volume playback when practical.

## QA failure examples

- literal script differs from generated speech;
- voice identity request violates policy or consent;
- music has unrequested vocals;
- source dialogue is muted unintentionally;
- dialogue is masked by music;
- layer begins in the wrong time domain;
- loop or cut clicks/pops;
- compressor pumps or limiter distorts;
- generated audio succeeded but was not applied;
- final export was not listened to after the mix changed.
