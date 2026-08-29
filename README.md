# ClipIt Agent Pack

ClipIt Agent Pack equips a shell- or MCP-capable agent to act as a practical video editor: ingest footage, understand transcripts, shape a story, assemble timelines, frame subjects, caption, generate supporting media, mix audio, render, deliver, publish, and prove the result is ready.

Pack version `2.0.0` is described by [`agent-pack.manifest.json`](agent-pack.manifest.json). It targets capability contract `clipit-agent-capabilities.v1`, requires ClipIt CLI `0.3.0` or newer, and keeps `clipit-operator` active for every ClipIt task.

## Connect ClipIt

Install the current CLI and use browser-linked login:

```bash
npm install -g @clipit-ai/cli@latest
clipit login
clipit doctor --json
clipit auth status --json
```

Use `clipit login --no-browser` in a headless terminal. For CI or a manually issued key, pass the secret only through hidden standard input:

```bash
printf '%s' "$CLIPPER_API_KEY" | clipit auth set-key --stdin
```

Never put a key in a prompt, skill file, repository, command-line argument, or log.

Install ClipIt's live credential-free CLI instructions for the host agent:

```bash
clipit agent install codex       # or claude, hermes, openclaw, generic, or another name
clipit agent doctor codex --json
clipit agent update codex
```

The CLI-generated instruction is the live connection layer. This repository adds the deeper editor/creator skill pack and Python REST/enterprise fallbacks.

## Install the Full Pack

### Codex or another AGENTS.md agent

Clone the repository and work from its root. The agent reads [`AGENTS.md`](AGENTS.md), keeps [`clipper/clipit-operator/SKILL.md`](clipper/clipit-operator/SKILL.md) active, and loads the smallest domain skill needed for each task.

### Claude Code

Clone the repository and work from its root. [`CLAUDE.md`](CLAUDE.md) routes Claude to the same operating and domain skills.

### Hermes

```bash
hermes skills tap add nplusm-Clippy/ClipIt-Agent-Pack

hermes skills install \
  clipper/clipit-operator \
  clipper/video-management \
  clipper/clip-creation \
  clipper/timeline-editing \
  clipper/project-sequence-management \
  clipper/creator-style \
  clipper/crop-reframing \
  clipper/caption-generation \
  clipper/thumbnail-generation \
  clipper/broll-generation \
  clipper/scene-alter \
  clipper/audio-production \
  clipper/blueprint-to-edit \
  clipper/delivery-qa \
  clipper/export-rendering \
  clipper/social-publishing \
  clipper/account-insights \
  clipper/machine-payments
```

`clipit-operator` is required. The remaining skills are installable domain modules; install the complete set for a general-purpose ClipIt editor.

## How an Agent Uses ClipIt

The authenticated server is the source of truth. Discover the live surface before guessing a tool or field:

```bash
clipit skills list --json
clipit skills describe <capabilityId> --json
clipit skills manifest --json
clipit media-guides list --json
clipit media-guides describe <guideId> --json
clipit tools list --json
clipit tools describe <functionName> --json
clipit context show --json
```

Use one execution owner per mutation, in this order:

1. A friendly `clipit <domain> <action>` command when it exactly covers the operation.
2. `clipit ask` for a multi-tool Clippy outcome.
3. `clipit run <functionName> --params @params.json` after live tool discovery.
4. The same discovered tools through the `clipit mcp stdio` bridge.
5. A script in `scripts/` only when CLI/MCP cannot express the operation or the enterprise exact contract requires it.

Do not replay the same uncertain mutation through another transport.

### Clippy workflows

```bash
clipit context use --video-id <videoId>
clipit ask "Find the strongest clip and prepare a review cut" --stream
```

If a workflow pauses, keep its job/conversation/approval IDs and use the exact printed approval or resume command:

```bash
clipit workflow status <jobId> --json
clipit workflow approve <jobId> --approval-id <approvalId> --decision approved
clipit workflow wait <jobId> --stream
```

### MCP

Configure an MCP-compatible client to launch:

```bash
clipit mcp stdio
```

The bridge uses the active CLI profile and exposes live ClipIt tools plus progressive resources through `resources/list` and `resources/read`:

- `clipit://instructions`
- `clipit://manifest`
- `clipit://skills/<capabilityId>`
- `clipit://media-guides/<guideId>`

Read the manifest first, then only the skill and media-guide resources needed for the current editing pass. Paid generation, publishing, deletion, and other gated mutations return `requiresConfirmation`; retry the same tool with `confirmed: true` only after the user approves the exact operation and cap.

### Python REST fallback

```bash
python3 -m pip install -r requirements.txt
python3 scripts/get_agent_instructions.py --target generic --format markdown
python3 scripts/list_videos.py
```

Every script supports `--help`. The scripts share CLI profiles and are not a second orchestration owner.

## Editorial Operating Model

The pack teaches agents to work in passes:

1. Ingest and source integrity.
2. Transcript/story paper edit.
3. A-roll assembly and pacing.
4. Format, crop, and visual context.
5. Captions and graphics.
6. B-Roll or selected-section Alter.
7. Dialogue, voiceover, music, and mix.
8. Whole-program delivery QA, then render/export/delivery/publish.

See the shared [editorial workflow](clipper/clipit-operator/references/editorial-workflow.md), [time/state model](clipper/clipit-operator/references/time-and-state.md), [outcome recipes](clipper/clipit-operator/references/outcome-recipes.md), and [media QA contract](clipper/clipit-operator/references/media-qa.md).

## Current Media Prompt Contracts

ClipIt selects and operates providers. Agents express typed intent through live ClipIt schemas and use the shared [media prompting contract](clipper/clipit-operator/references/media-prompting.md):

| Purpose | Current model route | Core prompt behavior |
| --- | --- | --- |
| Thumbnail and B-Roll still | `openai/gpt-image-2` on Replicate | Explicit create/edit/composite mode, reference roles, exact text, crop-safe composition, invariants |
| B-Roll image-to-video | `minimax/h3-max/image-to-video` on fal | Motion-first prompt, one camera idea, real-person continuity, no audio direction |
| Selected-section Alter | `google/gemini-omni-flash/v1.1/edit` on fal | One visual delta, preserve source identity/timing/framing/audio, “Keep everything else the same.” |
| Voiceover | `google/gemini-3.1-flash-tts` on Replicate | Literal text separate from performance direction and voice/language controls |
| Music | `minimax/music-2.6` on Replicate | Production brief separate from lyrics and ClipIt timeline/mix controls |

Do not use older model attributions or a remembered provider price. Run a current plan/preflight for the exact request.

## Skills

| Skill | Purpose |
| --- | --- |
| [clipit-operator](clipper/clipit-operator/SKILL.md) | Always-on CLI/MCP, context, approval, spend, resume, state, and verification rules |
| [video-management](clipper/video-management/SKILL.md) | Ingest, assets, source registration, readiness, transcription, safe removal |
| [clip-creation](clipper/clip-creation/SKILL.md) | Transcript-grounded suggestions, manual clips, saved-clip lifecycle, exact enterprise recipe |
| [timeline-editing](clipper/timeline-editing/SKILL.md) | Inspect, add, move, trim, split, and remove timeline placements |
| [project-sequence-management](clipper/project-sequence-management/SKILL.md) | Organize projects, sequences, tracks, and alternate versions |
| [creator-style](clipper/creator-style/SKILL.md) | Read/infer/update/apply creator and learned preferences |
| [crop-reframing](clipper/crop-reframing/SKILL.md) | Subject/context detection, aspect conversion, timed/stacked layouts |
| [caption-generation](clipper/caption-generation/SKILL.md) | Word-timed captions, presets, exact canonical styles |
| [thumbnail-generation](clipper/thumbnail-generation/SKILL.md) | GPT Image 2 thumbnail create/edit and image QA |
| [broll-generation](clipper/broll-generation/SKILL.md) | GPT Image 2 + H3 Max B-Roll plan/generate/apply/QA |
| [scene-alter](clipper/scene-alter/SKILL.md) | Gemini Omni Flash selected-section visual replacement and revert |
| [audio-production](clipper/audio-production/SKILL.md) | TTS, music, source audio, layers, processing, and mix QA |
| [blueprint-to-edit](clipper/blueprint-to-edit/SKILL.md) | Parse and execute long edit blueprints with durable checkpoints |
| [delivery-qa](clipper/delivery-qa/SKILL.md) | Current-artifact visual/audio/technical/authority completion gate |
| [export-rendering](clipper/export-rendering/SKILL.md) | Current-state render/export, resume, download, enterprise delivery |
| [social-publishing](clipper/social-publishing/SKILL.md) | Exact artifact/account publishing, scheduling, and status |
| [account-insights](clipper/account-insights/SKILL.md) | Live estimates/caps, usage, balance, and analytics |
| [machine-payments](clipper/machine-payments/SKILL.md) | Explicitly approved live-catalog credit top-ups |

## Approval, Spend, and Async Safety

- Inspect/plan first. Paid generation, render/export, publish/schedule, payment, deletion, and irreversible state changes require the reported confirmation gate.
- Use `--max-credits <approved-cap>` and a current estimate; do not copy example prices.
- Store returned job, workflow, approval, plan, resume, and artifact IDs. Query status before retrying.
- Generic jobs use `clipit jobs wait`; exports use `clipit exports wait`; workflows use `clipit workflow wait`.
- Provider completion is not application, QA, export, delivery, client selection, or publishing.

## Enterprise Workspace Exactness

Enterprise workspace keys are ClipIt-team authority, not a normal-user feature. Use one non-default named profile per workspace and verify the exact workspace before any client read or mutation:

```bash
clipit auth set-key --stdin --profile "enterprise-client-slug"
clipit auth use "enterprise-client-slug"
python3 scripts/verify_enterprise_workspace.py \
  --workspace-id "<expected-workspace-id>" \
  --profile "enterprise-client-slug"
```

Use Source Library registration, canonical snapshot identity, the complete approved caption object/hash, a read-only exact-delivery plan, the same capped confirmed request through resume, and an exact-lineage ready deliverable. Only the client may select it. Direct captioned legacy enterprise rendering and publishing a merely ready delivery are blocked.

The complete authority-preserving sequence and recovery rules are in [enterprise-exactness.md](clipper/clipit-operator/references/enterprise-exactness.md). Existing Python contract scripts and tests remain the executable source of truth.

## Development Validation

```bash
python3 -m unittest discover -s tests -v

for skill in clipper/*/SKILL.md; do
  python3 /mnt/c/Users/namas/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$(dirname "$skill")"
done
```

The test suite validates existing enterprise authority contracts, skill/manifest parity, reference packaging, current media terminology, and public B-Roll/thumbnail request shapes.

## License

MIT
