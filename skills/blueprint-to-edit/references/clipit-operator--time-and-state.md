# Time Domains and Canonical State

## Three time domains

Never pass a timestamp until its domain is named.

| Domain | Zero point | Typical use |
| --- | --- | --- |
| Source time | Beginning of the imported source video | Create a saved clip from source timestamps; transcript words and source analysis |
| Clip-local time | Beginning of the saved/selected clip | B-Roll placement, Alter selection, caption timing, audio layers inside a clip |
| Sequence time | Beginning of an editing sequence | Add, move, trim, split, and layer timeline clips |

Convert explicitly:

```text
clip_local = source_time - source_clip_start
source_time = source_clip_start + clip_local
sequence_time = timeline_clip_start + clip_local_offset
```

Account for trims, playback rate, splits, and preceding timeline gaps. Verify calculated ranges against current tool output before mutation.

## Identity map

- `videoId`: imported/registered source video.
- saved `clipId`: reusable clip cut from a video.
- `projectId`: top-level editorial container.
- `sequenceId`: timeline inside a project.
- timeline clip ID: one placement on one sequence track; use it for move/trim/split/remove.
- media layer ID: B-Roll, Alter, text, effect, or audio layer applied to a clip/timeline.
- `jobId`: asynchronous processing identity.
- export ID/job ID: one export of one verified editor state.
- deliverable ID: client-review object bound to an exact export lineage.

Do not substitute one ID type for another even when the underlying media is the same.

## Read-modify-read loop

1. Read the authoritative current object.
2. Record its ID, version/hash when supplied, timestamps, tracks/layers, and status.
3. Compute one bounded mutation.
4. Submit through one execution owner.
5. Read the object again.
6. Compare intended delta and preserved invariants.

For a batch, inspect the full batch result and resulting timeline rather than assuming every item succeeded.

## Stale-state rules

Any change to source bounds, sequence placement, aspect/framing, caption enablement/style, media layers, audio mix, quality, or outro policy may invalidate downstream state. After such a change:

- discard cached timeline/layout assumptions;
- refresh the canonical clip/project state;
- re-run relevant QA;
- create a new render/export tied to the new state;
- never publish an earlier artifact as current.

For enterprise work, retain the canonical editor version/hash/settings revision and exact caption hash. An exact export must prove the current snapshot lineage and output fingerprint.

## Layer and track ordering

Before placing media, inspect the existing tracks/layers and determine:

- visual z-order;
- audio track/mix authority;
- collision behavior;
- whether a move is absolute or ripple-based;
- whether a trim changes source in/out or timeline duration;
- whether an applied generation creates a new layer or replaces a selected section.

Never assume track names or default indices. Use live IDs from the current project/sequence.

## Async state machine

Keep these states separate:

```text
planned -> awaiting_approval -> submitted -> queued -> processing
        -> provider_completed -> qa_reviewed -> applied -> delivery_qa
        -> rendered -> exported -> ready_delivery -> client_selected -> published
```

Failures or warnings can occur at each transition. Provider completion does not prove application, QA, rendering, delivery, or publishing. Resume from the latest proved state.

## Source-audio authority

- B-Roll overlays do not replace source dialogue.
- Selected-section Alter preserves source audio unless the user separately requests a mix change.
- A generated voiceover or music bed becomes an explicit audio layer; it never silently overwrites source audio.
- Muting, replacing, or ducking source audio is a separate reviewed timeline/mix decision.
- Visual QA cannot certify audio. Inspect the final mix separately.

## Recovery receipt

Before ending an asynchronous turn, record:

```json
{
  "profile": "active profile name, never the key",
  "transport": "cli|ask|run|mcp|python",
  "targetIds": {},
  "timeDomain": "source|clip_local|sequence",
  "requestFingerprintOrIdempotencyKey": "when supplied",
  "approval": {"status": "...", "maxCredits": "..."},
  "jobId": "...",
  "workflowIds": {},
  "lastProvedState": "...",
  "nextReadOrResumeCommand": "..."
}
```

Never put secrets or signed URLs in the receipt.
