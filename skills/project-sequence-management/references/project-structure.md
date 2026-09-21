# Project Structure and Versioning

## Decide before creating

Inspect existing projects and answer:

- Is this a new editorial workstream or an alternate cut of an existing one?
- What is the primary delivery platform/aspect?
- Are there separate approval states or client versions?
- Does the edit need one sequence or several?
- Which source clips/assets are already registered?

Reuse when structure already matches. Create only when the user asked for a new container or the output genuinely needs an isolated timeline.

## Naming

Good project names combine source/campaign and purpose: `Podcast 42 Social Cuts`, `Q1 Launch Highlights`, `Client A Product Demo`.

Good sequence names distinguish version and destination: `Main 16x9`, `Vertical 9x16 v1`, `Client Review No Music`, `Approved Social Cut`.

Do not encode secrets, internal keys, or unstable job IDs in names.

## Resolution choices

Use the values exposed by the live schema. Common intent mappings include:

- landscape/general video: 1920x1080;
- lighter landscape preview: 1280x720;
- landscape 4K: 3840x2160;
- portrait short form: 1080x1920;
- square feed: 1080x1080.

Resolution/aspect decisions affect crop, captions, graphics, generated-media composition, and QA. Make them before detailed visual work.

## Alternate versions

Create a separate sequence when changes are structural or destination-specific. Keep one canonical owner for each version and record:

```text
projectId:
sequenceId:
purpose/platform:
resolution/frame rate:
source edit/version:
approval state:
current render/export:
```

Do not mix assets or approvals between sequences. Re-read the chosen structure immediately before timeline mutations and export.

## Handoff to timeline editing

`getProjectStructure` should provide the target sequence and track IDs. Use `addExistingClipToTimeline` for an already saved clip. Use clip-creation tools only when creating a new clip from source time. After placement, re-read the timeline and project structure to confirm duration and organization.

## Verification

- Correct profile/workspace owns the project.
- Project and sequence names explain their purpose.
- Resolution and frame rate match the brief.
- Returned sequence and default tracks exist.
- Active context points at the intended project/sequence.
- Alternate sequences remain distinguishable and do not inherit unverified delivery claims.
