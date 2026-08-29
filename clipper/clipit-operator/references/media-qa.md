# Media and Delivery QA

QA compares an inspectable artifact with the creative brief, typed intent, authoritative references, current timeline, and destination—not with the fact that a provider returned success.

## Evidence states

- `pass`: inspected evidence satisfies every fail-level criterion.
- `warning`: usable, but a visible trade-off remains.
- `fail`: a requested outcome, invariant, or delivery requirement is not met.
- `not_reviewed`: the media could not be inspected. Reviewer or sampling failure is never a pass.
- `waived`: the user explicitly accepts a named fail/warning for this artifact/version.

Record observations separately from inferences. A waiver does not repair the artifact and does not transfer to a regenerated version.

## Generated image QA

Download or open the actual image and check:

- requested create/edit/composite change;
- authoritative person, product, and logo fidelity;
- exact visible text, spelling, casing, and hierarchy;
- anatomy and object count;
- composition, focal hierarchy, and destination crop safety;
- lighting, palette, and style direction;
- every named invariant and Avoid item;
- file availability, aspect, and resolution metadata.

For thumbnails, inspect at reduced display size. The concept must remain legible and the face/product/text must not compete equally for attention.

## Generated video QA

Inspect the first and last frames plus frames near 10%, 25%, 50%, 75%, and 90%, and inspect around every material scene cut or high-difference transition.

Check:

- communication objective and requested motion;
- first/end reference compatibility;
- identity, anatomy, product, clothing, and object-count continuity;
- plausible motion and camera behavior;
- flicker, morphing, warping, texture crawl, temporal text/logo drift, or new subjects;
- duration and intended clip-local placement;
- framing and destination crop;
- actual application to the intended layer/range.

For selected-section Alter, compare source and output at matching timestamps. Only the requested visual delta may change. Confirm source action, timing, camera, framing, untouched objects, and audio remain aligned.

Visual inspection does not certify audio.

## Audio QA

Listen to the final mixed artifact, not only isolated generated audio:

- dialogue intelligibility and source-audio continuity;
- clipping, distortion, hum, sudden gain jumps, and abrupt cuts;
- voiceover words, pronunciation, pacing, emotion, and timing;
- music form, loop seam, fades, ducking, and competition with speech;
- sync between spoken content and visuals;
- unintended silence, duplicated layers, or source muting;
- loudness consistency appropriate to destination.

Generated speech must match the literal approved script. Generated music must not contain unrequested vocals or spoken words.

## Timeline QA

- correct project, sequence, tracks, and current IDs;
- no accidental gaps, collisions, overwritten layers, or off-by-one range errors;
- cuts preserve speaker meaning and continuity;
- B-Roll, captions, Alter, graphics, and audio begin/end in the intended time domain;
- reframing changes do not crop the active subject or oscillate distractingly;
- all layers survive a current-state read and preview.

## Delivery readiness

Before calling an edit ready, inspect:

```text
Story: hook, complete thought, pacing, clean ending
Picture: aspect, framing, identity, continuity, overlays, safe areas
Text: transcript fidelity, spelling, captions, graphics, crop safety
Audio: dialogue, mix, sync, fades, no clipping
Technical: current render, duration, resolution, playable artifact
Authority: exact current state, approval/cap, enterprise lineage/client selection
Destination: platform limits, title/copy/account, publish readiness
```

Fail-level findings block export/publish claims until fixed or explicitly waived. Warnings stay visible in the handoff.

## QA receipt

```json
{
  "artifactId": "current artifact/version",
  "briefVersion": "brief identity",
  "inspection": ["what was opened, sampled, or heard"],
  "status": "pass|warning|fail|not_reviewed|waived",
  "findings": [
    {"severity": "fail|warning", "criterion": "...", "evidence": "...", "action": "..."}
  ],
  "audioReviewed": true,
  "waivers": [],
  "readyFor": "review|render|export|delivery|publish|none"
}
```

If a later mutation changes the artifact, this receipt is stale and QA must run again.
