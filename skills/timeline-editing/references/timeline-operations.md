# Timeline Operations

## Read first

`getTimelineContents` should establish:

- sequence and resolution/frame rate;
- track IDs/types/order;
- each timeline placement ID;
- referenced saved clip/source;
- sequence start/end and duration;
- source in/out or clip-local bounds when returned;
- overlays/audio layers and collision context.

If the response is missing a required identity or time basis, stop and discover a more specific read tool rather than guessing.

## Add

Use `addExistingClipToTimeline` for a saved ClipIt clip. Use clip-creation tools when the request is to create a new saved clip from source timestamps. Choose a sequence time and live track ID. Inspect the resulting placement and full timeline.

When assembling several clips, calculate a proposed paper edit first. Add in story order, then tighten rhythm in a separate pass.

## Trim

Clarify whether the user wants:

- a new sequence in/out;
- a new source in/out;
- a shorter duration from one edge;
- preservation of downstream timing; or
- ripple closure.

Respect minimum duration and current source bounds from the live schema. After trimming, verify the exact retained words/action and the neighboring audio join.

## Move

Use an absolute sequence position and live target track. Check occupancy and z-/mix-order before moving. A move between tracks may change visibility or audio behavior even when timestamps remain the same.

## Split

Confirm whether the split timestamp is sequence time or placement-local time. Inspect both resulting IDs and bounds. Do not assume which half retains the original ID. If one half should be removed, split and re-read before deletion.

## Remove

Resolve the exact timeline placement and show the effect on sequence duration/gaps. Removing a placement does not necessarily delete the saved library clip. Use the deletion-specific command only when the user explicitly asks to delete source/library media.

## Batch edits

For a complex assembly:

1. Snapshot current contents.
2. Produce an ordered edit list with operation, target ID, time domain, intended new bounds/position, and expected adjacent effect.
3. Apply one story pass.
4. Re-read and compare.
5. Apply pacing, framing/graphics, and audio in later passes.

Do not submit overlapping mutations concurrently. Stop on partial failure and reconcile current state before resuming.

## Verification

- Every intended source appears once unless repetition is deliberate.
- No unintended black gaps, overlaps, hidden video, or doubled audio.
- Cuts preserve sentence meaning and motion continuity.
- Total duration and aspect match the brief.
- Timed captions, B-Roll, Alter, crop, graphics, and audio still align after structural changes.
- A full preview passes before render/export.
