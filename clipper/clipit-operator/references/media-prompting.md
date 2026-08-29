# Media Prompting Contract

Contract version: `media-prompting-contract.v2`.

ClipIt owns provider selection, credentials, routing, and current capability controls. The agent supplies a typed creative intent through the live ClipIt tool schema; it does not call a remembered provider endpoint or invent a model option.

Before paid generation:

1. Name the asset purpose, destination, time range, and current source-of-truth media.
2. Choose create, edit, animate, voiceover, or music mode.
3. Map every reference to one role.
4. Name identity, product, logo, text, composition, timing, and audio invariants.
5. Keep provider prompt, provider controls, timeline placement, and mix controls separate.
6. Describe the live tool, plan/preflight, set a spend cap, and obtain confirmation.
7. Inspect the returned asset. Provider completion is not a QA pass.

Never invent a reference URL, brand asset, quote, voice identity, capability, price, or approval.

## GPT Image 2: thumbnails and source stills

Current route: `openai/gpt-image-2` on Replicate through ClipIt.

Choose one mode:

- Create: no supplied image controls identity or layout.
- Edit: a supplied frame/image controls identity, product, logo, composition, or layout.
- Composite: each reference receives one explicit role.

Prompt order:

```text
Intended use and mode:
Primary request:
Reference map:
Subject:
Scene/background:
Composition and crop-safe placement:
Camera/lens/depth:
Lighting:
Color/material/rendering style:
Exact visible text:
Invariants:
Avoid:
```

Rules:

- Use one dominant focal point and explicit relative placement/scale.
- Quote required visible text exactly and keep it short. Specify placement, hierarchy, and contrast.
- For an edit, lead with “Change only …” and list the invariants whose drift would make the output unusable.
- Map references by index and role: “Image 1 = person identity; Image 2 = product; Image 3 = style only.”
- Keep faces, products, logos, and text inside the destination crop-safe area.
- Put only likely, high-value failures in Avoid. Do not write a generic negative wall.
- Aspect, resolution, and quality are API controls, not prompt adjectives.

Edit template:

```text
Intended use: <thumbnail or B-Roll still>. Mode: edit.
Primary request: Change only <one clear delta>.
Reference map: Image 1 controls <identity/composition>; Image 2 controls <product/style/logo>.
Preserve unchanged: <face, body, pose, clothing, product geometry, logo, layout, camera, background, existing text as applicable>.
Composition and crop safety: <destination layout and safe area>.
Exact text: Replace "<old>" with "<new>"; preserve all other text/layout.
Avoid: <specific drift, anatomy, duplication, logo, unrelated text, crop failures>.
```

## MiniMax H3 Max: B-Roll image-to-video

Current provider model: `minimax/h3-max/image-to-video` on fal through ClipIt. The source still owns subject, scene, style, and framing. Prompt motion and time structure; do not redescribe the whole still.

Prompt order:

```text
Shot objective:
Camera behavior:
Subject action:
Environmental motion:
Timing beats, only when needed:
End state, only with an end frame:
Continuity and identity invariants:
```

Rules:

- Use one coherent camera behavior and one clear subject/environmental action.
- Prefer physically plausible, restrained motion: breath, eye movement, one hand action, fabric response, slow dolly, controlled pan, stable follow.
- For real people, preserve face, body proportions, age appearance, skin tone, hair, clothing, and identity. Reduce motion when fidelity is more important than spectacle.
- Single-image mode ends in a plausible continuation. Start/end mode describes one continuous transformation between compatible frames, not an unrelated cut.
- Do not direct dialogue, music, sound effects, or ambience. ClipIt discards H3 audio and source audio remains authoritative.
- Duration, aspect, resolution, and prompt expansion are provider fields, not prose.
- Default to 5–10 seconds; use 10–15 only for a real multi-beat shot.

Template:

```text
Shot objective: <communication purpose>.
Camera: <one behavior>.
Subject action: <one natural action with pace/direction>.
Environment: <one or two subtle motions>.
Timing: <optional beats>.
End state: <only when required>.
Continuity: preserve <identity, clothing, object count, geometry, lighting direction, composition>; no cuts, morphing, flicker, text, logos, or new subjects.
```

Use balanced prompt expansion normally, quality only when safe enrichment is acceptable, and disabled for identity/product-sensitive motion or exact invariants—only when the live tool exposes that control.

## Gemini Omni Flash 1.1: selected-section Alter

Current provider model: `google/gemini-omni-flash/v1.1/edit` on fal through ClipIt.

The selected source section owns everything not explicitly changed. Request one coherent visual delta per generation.

Prompt order:

```text
Requested visual change.
Essential preservation invariants.
Specific likely failures to avoid.
Continuous-shot instruction.
Keep everything else the same.
```

Template:

```text
<Requested visual change>. Preserve <every real person's identity, face, body, age appearance, skin tone, hair, clothing, source action, timing, camera, framing, lighting, and untouched scene elements that matter>. Avoid <specific likely drift>. Keep this as one continuous shot with the same timing and framing. Keep everything else the same.
```

Do not request speech, voice, music, sound, or audio replacement. ClipIt preserves the selected source audio. Do not put duration, aspect, first/last frame, or negative-prompt parameters into the instruction unless live discovery shows that support. Split broad transformations into separate selected sections.

## Gemini Flash TTS: voiceover

Current route: `google/gemini-3.1-flash-tts` on Replicate through ClipIt.

Keep the literal spoken words in the text field. Put performance direction only in the prompt field.

```text
text:
<literal words to speak>

prompt:
Voice profile: <non-imitative vocal qualities>.
Scene: <podcast intro, walkthrough, reflective close, etc.>.
Delivery: <pace, rhythm, emotional intention>.
Emphasis: <specific words and pauses>.
Pronunciation: <term -> pronunciation, only if needed>.
Restraints: natural and conversational; do not add, omit, or paraphrase the supplied words.

voice: <allowlisted voice>
language_code: <matching BCP-47 code>
```

Do not imitate a living person or private individual's voice. Fit the script to target duration before generation, keep pronunciation notes minimal, and check UTF-8 byte limits through the live schema.

## MiniMax Music 2.6: music bed

Current route: `minimax/music-2.6` on Replicate through ClipIt.

Keep the provider style prompt, lyrics, and ClipIt mix controls separate. Default to instrumental for a dialogue bed unless the user explicitly wants lyrics.

Style-prompt order:

```text
Use and form:
BPM or tempo range:
Genre/subgenre:
Mood and emotional arc:
Core instruments:
Rhythm/groove:
Production texture and mix character:
Section-by-section energy curve:
Vocal character, only for lyrics:
Musical exclusions:
```

Instrumental template:

```text
Use: <background bed/intro/reveal/outro>. Form: <short intro -> build -> restrained peak -> clean loop/outro>. Tempo: <BPM/range>. Genre: <specific genre>. Mood: <two or three compatible qualities>. Instruments: <primary/support/bass/percussion>. Groove: <rhythmic feel>. Production: <texture, space, saturation, width>. Energy curve: <section timing/intensity>. Exclude: vocals, spoken words, abrupt drops, distracting lead melody, and <task-specific exclusions>.
```

Do not name a living artist as a style target. Use musical attributes instead. Put volume, placement, fades, loops, and ducking in ClipIt mix controls. For lyrics, use `[Intro]`, `[Verse]`, `[Chorus]`, `[Bridge]`, and `[Outro]` only as duration permits.

## Real-person continuity checklist

For every referenced real person:

- identify which supplied media owns identity;
- preserve face geometry, skin tone, age appearance, hair, body proportions, clothing, accessories, and handedness where visible;
- preserve object count, interaction, eyeline, and screen direction;
- request no new people unless explicit;
- use conservative camera/subject motion when fidelity matters;
- compare source and output at matching timestamps for video edits;
- reject morphing, face swaps, anatomy drift, duplicated limbs, sudden wardrobe changes, and inconsistent lighting.

Never claim identity continuity from a provider response alone.
