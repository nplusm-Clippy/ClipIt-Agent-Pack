# Editorial Workflow

## Build the brief before the edit

Capture only facts that affect decisions:

```text
Outcome:
Audience and platform:
Target duration and aspect:
Primary message or emotional turn:
Source-of-truth video, transcript, project, sequence, and clip IDs:
Required moments or quotes:
Must preserve:
May change:
Creator/brand constraints:
Reference edit or blueprint:
Approval and spend cap:
Definition of done:
```

If an important field is unknown, inspect available context first. Ask only for a choice that would materially change the edit. Never invent brand assets, quotes, faces, products, or permission.

## Work in passes

Re-read the affected state after each pass. A later pass must not silently undo an earlier approved choice.

### 1. Ingest and source integrity

- Confirm the intended source and active profile.
- Wait for upload/import processing.
- Check duration and audio health.
- Reuse an existing transcript when suitable; transcribe before semantic clip discovery or word-synced captions.
- Preserve source identity and source audio as authority.

### 2. Story and paper edit

- Read the full transcript around candidate moments, not isolated quotes.
- Identify hook, promise, development, payoff, and clean exit.
- Prefer a complete thought over arbitrary duration compliance.
- Remove throat-clearing, repetition, dead air, and context that does not serve the promise.
- Preserve meaning. Do not splice words into a claim the speaker did not make.

For multiple candidates, state why each works and what audience response it serves before creating them.

### 3. Assembly and rhythm

- Create or select the project/sequence and inspect its current timeline.
- Place the A-roll structure first.
- Use source time for extracting a saved clip, clip-local time for overlays inside a clip, and sequence time for timeline placement.
- Make cuts at linguistic, emotional, or motion boundaries.
- Check collisions, gaps, discontinuities, and audio joins after every timeline mutation.
- Use B-Roll to clarify, prove, pace, or reset attention—not to wallpaper every sentence.

### 4. Format and framing

- Choose the destination aspect before detailed graphics or crops.
- Inspect faces, speakers, products, demos, and intentional off-screen content.
- Apply the least invasive crop strategy that keeps the visual idea readable.
- For timed or multi-speaker reframing, preview transitions and preserve identity; do not overreact to momentary detections.

### 5. Captions and graphics

- Keep captions verbatim unless the user requests editorial text changes.
- Check reading speed, line breaks, safe areas, speaker changes, and brand style.
- Use a consistent hierarchy. Graphics should answer a communication need: identify, explain, quantify, orient, or emphasize.
- Protect exact approved enterprise style fields and canonical state lineage.

### 6. Generated visual media

- Decide whether the need is a still, B-Roll motion shot, or selected-section Alter.
- Write a typed intent and provider prompt using `media-prompting.md`.
- Generate only approved concepts and apply them to the intended time range.
- Inspect identity, continuity, timing, crop, text, and source-audio preservation before accepting.

### 7. Audio

- Analyze the existing mix before changing it.
- Establish clear source dialogue first; then add voiceover, music, and supporting layers.
- Use ducking, fades, looping, EQ/dynamics, and level changes as timeline/mix controls, not generation prose.
- Avoid masking words, clipping peaks, abrupt joins, or unintended source muting.

### 8. Polish and delivery

- Watch the whole result in order at least once, then inspect boundaries and sampled frames.
- Run delivery readiness QA against the destination platform and the brief.
- Resolve fail-level findings or obtain an explicit waiver.
- Render/export the current verified state only.
- Publishing, scheduling, client selection, and payment remain distinct authority gates.

## Creative decision rules

- Every edit should serve comprehension, emotion, credibility, rhythm, or platform fit.
- Use contrast intentionally: wide/tight, still/moving, information/emotion, silence/impact.
- Let a strong human performance breathe. More cuts and generated assets do not automatically improve it.
- Match visual specificity to spoken specificity. A concrete claim deserves concrete evidence; an abstract idea may use restrained metaphor.
- Prefer one strong direction and one fallback over uncontrolled variant generation.
- When feedback says an output “feels wrong,” diagnose story, timing, framing, style, identity, or mix separately before regenerating.

## Pass receipt

After each pass, retain:

```text
Read state:
Mutations submitted:
Resulting IDs/version:
Observed change:
Open risks:
Approval needed next:
```

This receipt lets another agent resume without replaying completed work.
