---
name: clipit-operator
description: Operate ClipIt safely end to end through its CLI, MCP bridge, Clippy workflows, or Python REST fallback. Use for any ClipIt editing, creation, media generation, export, delivery, publishing, account, or multi-step workflow so tool discovery, context, approvals, spend caps, asynchronous resume, and verification stay coherent.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Video Editing, CLI, MCP, Clippy, Workflow Safety]
  hermes:
    tags: [ClipIt, Video Editing, CLI, MCP, Clippy, Workflow Safety]
    requires_toolsets: [terminal]
---

# ClipIt Operator

This is the always-installed operating layer for every ClipIt task. Load the smallest domain skill that matches the requested edit, but keep this skill's execution rules active across the whole session.

## Start Here

1. Run `clipit doctor --json` and `clipit auth status --json`. Never print a credential.
2. Establish the target with `clipit context show --json`; set only known IDs with `clipit context use`.
3. Discover the live surface before guessing a tool or parameter:
   - `clipit skills list --json`
   - `clipit skills manifest --json`
   - `clipit skills describe <capabilityId> --json`
   - `clipit media-guides list --json`
   - `clipit media-guides describe <guideId> --json`
   - `clipit tools list --json`
   - `clipit tools describe <functionName> --json`
4. Read before changing: inspect the video, clip, project, sequence, timeline, transcript, creator profile, or delivery state that owns the requested outcome.
5. Write a compact creative brief and definition of done. For editing work, use the pass order in [editorial-workflow.md](references/editorial-workflow.md).
6. Preflight paid work and set a user-approved `--max-credits` cap. Plan calls do not authorize generation.
7. Execute through exactly one owner, record returned IDs and state tokens, wait or resume, then verify the resulting artifact rather than the request alone.

## Execution Hierarchy

Choose one transport for a mutation and do not repeat it through another transport:

1. Use a purpose-built CLI command when it expresses the operation exactly.
2. Use `clipit ask` for a named, multi-tool Clippy outcome that benefits from server orchestration.
3. Use `clipit run <functionName>` after live discovery for a tool without a friendly command.
4. In an MCP client, use the ClipIt tools exposed by `clipit mcp stdio`; the same confirmation rules apply.
5. Use this pack's Python scripts only when the CLI/MCP surface is unavailable or an enterprise exactness recipe explicitly requires them.

Read [tool-transport.md](references/tool-transport.md) before the first mutation, when switching transport, or when an operation pauses.

## Context and State

- Treat source time, clip-local time, and sequence time as different coordinate systems.
- A library clip ID, timeline clip ID, sequence ID, render job ID, export ID, and deliverable ID are not interchangeable.
- Re-read current state after every material mutation. Never chain later edits from a stale snapshot.
- Preserve the authoritative source audio unless the user explicitly changes the mix. Generated B-Roll and Alter provider audio are not source authority.
- For exact enterprise work, use one named profile per workspace and follow [enterprise-exactness.md](references/enterprise-exactness.md).

Read [time-and-state.md](references/time-and-state.md) before timeline, crop, Alter, audio-placement, blueprint, export, or recovery work.

## Approval and Spend

- Read-only inspection and planning can run without mutation approval.
- Paid generation, rendering/export, publishing/scheduling, payment, deletion, and other user-visible irreversible actions require the CLI/MCP confirmation gate unless the user has explicitly approved that exact action and cap.
- Present the target, operation, live estimate, cap, and expected artifact before approval. Do not quote a remembered price.
- If an MCP call returns `requiresConfirmation`, stop. Retry once with `confirmed: true` only after approval.
- If a CLI workflow exits with code 12, use the printed approval command or choose a cheaper decision; do not bypass the pause.
- Reuse an idempotency key only for the exact same request after an unknown outcome.

## Asynchronous Work

- Save the returned `jobId`, `conversationId`, `approvalId`, plan hash, resume token, and artifact IDs immediately.
- Resume the same operation; do not start a replacement because progress is unchanged.
- Use `clipit jobs wait`, `clipit exports wait`, or `clipit workflow wait` for the correct job family.
- A transport success is not an editorial success. Inspect generated media and run delivery QA before saying the work is complete.

## Creative and Media Rules

- Start from a typed creative brief: audience, platform, objective, source truth, invariants, edit scope, and acceptance criteria.
- Apply creator style as constraints, not as a substitute for the user's request.
- Keep provider prompt, provider controls, timeline placement, and audio-mix instructions separate.
- Read [media-prompting.md](references/media-prompting.md) before image, B-Roll, Alter, TTS, or music generation.
- Read [media-qa.md](references/media-qa.md) before accepting generated media or final delivery.
- Use [outcome-recipes.md](references/outcome-recipes.md) for multi-skill edit packages.

## Completion Contract

Report the exact target and resulting IDs, what changed, what was inspected, any warnings or waivers, spend against the approved cap, and the next authority checkpoint. Use `blocked` when a required capability, approval, identity, or QA proof is missing. Never describe a planned, queued, provider-completed, or merely rendered operation as fully delivered.
