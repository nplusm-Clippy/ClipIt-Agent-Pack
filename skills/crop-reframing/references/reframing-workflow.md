# Reframing Workflow

## Choose the strategy

| Need | Strategy |
| --- | --- |
| Preserve the entire source image in a new aspect | Fit/full-frame with an intentional background treatment |
| Stationary subject | One normalized focal point or static crop |
| Layout changes at known times | Timed crop-layout segments |
| Moving subject with meaningful boundaries | Split/timed segments, then static decisions per segment |
| Library clip can be framed automatically | Auto-frame and inspect |
| Explicit two-speaker upper/lower vertical layout | Stacked-speaker workflow |

Do not default to aggressive fill-crop when important context would be removed.

## Visual analysis

Use visual-context analysis for slides, charts, posts, products, screens, signs, or other information that must remain visible. Use subject detection for concrete targets such as `human face, person`, `microphone, mic`, or `product, packaging, item being held`.

If confidence is low, broaden the noun phrase once. If several subjects are high-confidence and user intent does not resolve them, ask which one owns the frame. Do not keep spending on repeated detection without a new hypothesis.

## Coordinate normalization

Detection bounding boxes may be pixels `[x1, y1, x2, y2]`; crop application may require normalized `0..1` values. With authoritative `frameWidth` and `frameHeight`:

```text
centerX = ((x1 + x2) / 2) / frameWidth
centerY = ((y1 + y2) / 2) / frameHeight
x = x1 / frameWidth
y = y1 / frameHeight
width = (x2 - x1) / frameWidth
height = (y2 - y1) / frameHeight
```

Validate bounds and clamp only when the live crop contract says to. Never normalize using output canvas dimensions when the bbox came from the source frame.

## Static versus timed

Inspect sampled subject centers. If movement, scene changes, or protected context make a single frame invalid, use timed segments or split at a natural boundary. Avoid rapid crop oscillation. Hold layouts long enough to feel intentional and change on a cut, speaker turn, or visual-purpose transition.

Timed segment timestamps are clip-local unless the live schema states otherwise. Cover the full intended range, deliberately fill or preserve gaps, and avoid overlaps.

## Stacked speakers

Use only for an explicit upper/lower two-speaker request. Read the live tool contract, ensure the saved editor snapshot requirement is met, then let the all-in-one operation own detection and preset application. If it returns `EDITOR_SNAPSHOT_REQUIRED`, stop and report that no generation should be retried until the required snapshot exists. Do not call `redetectFaces` as a compensating retry.

## QA sample points

Inspect:

- first and last frame;
- every scene cut;
- every timed-layout boundary on both sides;
- each speaker's representative turn;
- maximum subject movement;
- moments with slides, products, hands, or on-screen text;
- caption-safe and platform-safe regions.

Fail when the active subject, key product/context, or required text is materially cropped; when framing jumps without editorial cause; or when a stale render/export is still presented as current.
