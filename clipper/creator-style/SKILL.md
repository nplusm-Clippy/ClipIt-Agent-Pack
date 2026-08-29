---
name: clipper-creator-style
description: Read, infer, update, and apply ClipIt creator preferences and learned editing facts across thumbnails, B-Roll, captions, framing, audio, and social packages. Use when the user asks to match their style, brand, audience, recurring edit preferences, or learn a correction for future work.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Creator Profile, Brand Style, Personalization, Creative Direction]
  hermes:
    tags: [ClipIt, Creator Profile, Brand Style, Personalization, Creative Direction]
    requires_toolsets: [terminal]
---

# ClipIt Creator Style

Use with `clipit-operator`. Read [creator-profile.md](references/creator-profile.md) before inferring, writing, or applying persistent preferences.

## Operating loop

1. Read `getCreatorProfile` and, when durable learned preferences matter, `getUserLearningProfile`.
2. Separate explicit facts, inferred patterns, task-only direction, and contradictions.
3. When the profile is sparse and history exists, use `inferCreatorProfile` with preview/no-save first unless the user asked to save automatically.
4. Ask for review only when a missing or conflicting preference materially affects the output.
5. Update only confirmed fields. Partial updates must preserve every omitted field.
6. Translate relevant profile fields into the current creative brief; do not dump the whole profile into every media prompt.
7. For an explicit durable correction, use `saveUserProfileFact` with explicit provenance and locking when the live schema supports it.
8. Verify the saved profile/fact with a fresh read.

## Tool family

The current server commonly exposes:

- `getCreatorProfile`
- `updateCreatorProfile`
- `inferCreatorProfile`
- `getUserLearningProfile`
- `saveUserProfileFact`

Describe the live tool before mutation.

## Application rules

- The current user request outranks learned preferences; explicit corrections outrank inference.
- B-Roll planning loads creator profile context automatically. Thumbnail, standalone image, caption, and social work require explicit retrieval/application of relevant fields.
- Treat brand colors, logos, products, and people as authoritative only when supplied/confirmed.
- Describe an audience by goals, frustrations, knowledge, and context—not stereotypes.
- Creator style constrains choices; it does not replace story purpose, source truth, platform requirements, or media prompt contracts.
- Do not save one-off task directions as durable preferences without user intent.

## Completion

Report which fields were read, inferred, explicitly confirmed, updated, or applied; name any contradictions left unresolved. A successful profile update does not prove a generated asset matches the style—inspect the actual media.
