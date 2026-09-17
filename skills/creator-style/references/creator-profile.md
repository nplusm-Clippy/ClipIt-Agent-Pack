# Creator Profile and Style Application

## Evidence classes

Classify every preference:

1. Explicit locked fact: direct durable instruction such as “always keep both hosts visible.”
2. Explicit current-task direction: applies to this edit only unless the user asks to remember it.
3. Inferred pattern: derived from existing transcripts/history; review before relying on high-impact choices.
4. Default: neutral platform/product behavior, not a user preference.

When two facts conflict, prefer the newest explicit instruction and surface the conflict before overwriting locked intent.

## Common profile fields

- content niche and platform destinations;
- preferred tone;
- audience goals, frustrations, desires, and knowledge;
- brand colors and supplied identity assets;
- lighting preference and visual mood;
- recurring caption, crop, duration, publishing, or audio preferences from the learning profile.

Only use fields exposed by the live schema. Validate brand colors as supported hex values and keep the allowed count.

## Inference

Profile inference can use recent video/transcript history to propose niche, tone, audience, and visual direction. It cannot reliably discover private brand rules, exact colors, legal approvals, destination accounts, or user intent.

Use preview/no-save first when possible. Present:

```text
Observed evidence:
Inferred preference:
Confidence/ambiguity:
Fields still requiring user input:
```

Never treat demographics, protected attributes, or a single video as a durable creative identity.

## Applying style to a brief

Translate profile data into only the relevant decisions:

| Task | Relevant profile context |
| --- | --- |
| Clip selection | audience pain/desire, tone, platform, usual duration |
| Captions/graphics | confirmed colors, typography/layout preferences, reading style |
| Thumbnail | audience promise, visual mood, colors, supplied identity/product assets |
| B-Roll | niche, visual mood, lighting, colors, audience comprehension need |
| Crop/reframe | recurring subject-preservation and platform rules |
| Audio | tone, energy, voice/music preferences, dialogue priority |
| Social copy | platform, tone, audience, explicit messaging rules |

The brief should cite profile fields as constraints and still name the task's specific objective.

## Saving facts

Save a durable fact only when the user indicates recurrence: “always,” “from now on,” “remember,” “my default,” or a clear correction to existing memory. Record the narrowest actionable fact, its source as explicit, and lock it when the live tool permits.

Do not save:

- secrets or credentials;
- private sensitive facts unnecessary to editing;
- transient clip IDs, job IDs, signed URLs, or approval state;
- an inferred preference as explicit;
- generated media quality judgments without user confirmation.

## Verification

Re-read the profile after mutation. For creative outputs, separately compare the actual result against the applied constraints. If it fails, diagnose the prompt/application before rewriting the persistent profile.
