# Tool Transport, Discovery, and Resume

## Authenticate and verify

Prefer browser-linked login:

```bash
npm install -g @clipit-ai/cli@latest
clipit login
clipit doctor --json
clipit auth status --json
```

Use `clipit login --no-browser` for a headless terminal. Use `clipit auth set-key --stdin` only for CI, a manually created key, or a named enterprise workspace profile. Never pass a key as a command-line argument or place it in a skill file.

## Discover, then execute

The authenticated server is the source of truth for current capabilities and schemas:

```bash
clipit skills list --json
clipit skills manifest --json
clipit skills describe <capabilityId> --json
clipit media-guides list --json
clipit media-guides describe <guideId> --json
clipit tools list --json
clipit tools describe <functionName> --json
```

Use the manifest as the compact compatibility and routing contract. Load only the capability and media-guide bodies relevant to the current pass, then discover the exact executable tool schema. Do not infer parameters from a remembered tool name. Describe the chosen tool in the current profile and environment, construct a JSON parameter file from that schema, and validate IDs against a fresh read.

### Friendly CLI command

Use a friendly domain command when it exactly covers the task. It provides validation, confirmation, spend guards, output normalization, and the correct job waiter.

```bash
clipit clips create --video-id <videoId> --start 12 --end 42 --title "Strong hook" --confirm --json
clipit thumbnails generate --clip-id <clipId> --prompt "..." --confirm --max-credits <approved-cap> --json
```

### Direct dynamic tool

Use a dynamic tool only after discovery:

```bash
clipit tools describe <functionName> --json
clipit run <functionName> --params @params.json --json
```

Add `--confirm` and `--max-credits <approved-cap>` when the described tool mutates, spends, generates, publishes, or deletes. A confirmation flag is not a substitute for user authorization.

### Clippy workflow

Use `clipit ask` for an outcome that naturally spans several tools:

```bash
clipit context use --video-id <videoId>
clipit ask "Find the strongest clip and prepare a review cut" --stream
```

Prefer a named server workflow/bundle when its outcome matches. Do not launch a second local executor against the same edit. If a workflow pauses, continue it through `clipit workflow approve`, `clipit workflow status`, and `clipit workflow wait` with the returned identifiers.

### MCP bridge

Configure the MCP client to launch:

```bash
clipit mcp stdio
```

The bridge supplies `tools/list`, `tools/call`, `resources/list`, and `resources/read` through the active CLI profile. Its progressive resources are:

- `clipit://instructions`
- `clipit://manifest`
- `clipit://skills/<capabilityId>`
- `clipit://media-guides/<guideId>`

Read `clipit://manifest` first, then only the skill and guide resources needed for the task. Treat MCP tool schemas as live. If a call returns `requiresConfirmation`, show the exact operation and estimate, obtain approval, and retry the same tool once with `confirmed: true`. Do not also run the equivalent CLI command.

### Python REST fallback

Use scripts in `scripts/` only when the live CLI/MCP surface cannot express the operation or the documented enterprise exact-delivery contract requires them:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/get_agent_instructions.py --target generic --format markdown
python3 scripts/<operation>.py --help
```

Scripts are fallback bindings, not a parallel orchestration system. Keep the active profile, approval cap, idempotency key, job ID, and artifact IDs identical when falling back. Never replay an uncertain mutation through a different transport.

When `clipit ask` itself is unavailable, `python3 scripts/orchestrate.py "<goal>" --video-id <id>` is its workflow fallback. If it exits awaiting approval, use the exact returned job/approval IDs with `approve_workflow.py`; do not launch a new orchestration job.

## One execution owner

For each mutation, explicitly assign one owner:

- friendly CLI command;
- one `clipit ask` workflow;
- one dynamic CLI tool call;
- one MCP tool call; or
- one Python script.

Other agents may inspect or critique, but they must not submit the same mutation. The owner records request intent, target IDs, confirmation/cap, response ID, and resume state.

## Context

Use `clipit context show --json` before implicit-ID commands. Use `clipit context use --video-id`, `--clip-id`, `--project-id`, or `--sequence-id` only with an ID obtained from the active profile. Clear stale context when changing client or project. Explicit IDs are preferred for destructive, paid, publishing, and enterprise actions.

## Confirmation and exit behavior

- Exit `0`: command accepted or completed; inspect the returned state.
- Exit `12`: approval required, workflow paused, or cap exceeded. Follow the printed approval/resume path.
- Exit `13`: insufficient credits or a spend limit. Do not silently raise the cap or buy credits.
- Auth, permission, network, and server errors must remain distinct. Preserve a returned request ID for support.

Paid commands should include a live `--max-credits` limit. If a dynamic tool cannot produce an estimate, report that the estimate is unavailable and require explicit confirmation instead of inventing a price.

## Jobs and recovery

Use the waiter for the returned resource:

```bash
clipit jobs wait <jobId> --stream
clipit exports wait <exportId> --stream
clipit workflow wait <workflowJobId> --stream
```

An unchanged percentage is not failure. Read phase, message, heartbeat, and stalled signals. On timeout or unknown transport outcome, query status first. Resume with the same job or workflow identity. Reuse an idempotency key only when every request field and source asset are unchanged.

Record separate states: `planned`, `awaiting_approval`, `queued`, `processing`, `provider_completed`, `applied`, `qa_passed`, `exported`, `delivered`, and `published`. Never collapse these into “done.”
