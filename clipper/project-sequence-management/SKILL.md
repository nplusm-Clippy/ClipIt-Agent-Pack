---
name: clipper-project-sequence-management
description: Create, inspect, and organize ClipIt editing projects, sequences, and their default tracks. Use when starting an edit, choosing the correct sequence, managing alternate cuts or platform versions, or understanding project structure before timeline mutations.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Project, Sequence, Editorial Organization, Timeline]
  hermes:
    tags: [ClipIt, Project, Sequence, Editorial Organization, Timeline]
    requires_toolsets: [terminal]
---

# ClipIt Project and Sequence Management

Use with `clipit-operator`. Read [project-structure.md](references/project-structure.md) before creating or reorganizing a project, and load timeline-editing before changing placements.

## Model

- A project is the top-level editorial container.
- A sequence is one timeline/version within a project.
- Tracks belong to a sequence.
- Timeline placements belong to tracks and reference saved clips or media layers.

Do not collapse these identities.

## Operating loop

1. Run `clipit context show --json` and identify any active project/sequence.
2. Discover/describe the current project tool.
3. Use `listProjects` or `getProjectStructure` before deciding to create anything.
4. Reuse the intended project/sequence when it exists; create only the requested new editorial container.
5. Select output resolution/aspect and frame rate from the primary destination before detailed assembly.
6. Retain returned project, sequence, and track IDs and set context explicitly.
7. Re-read project structure after creation and before timeline work.

## Tool family

The current server commonly exposes:

- `listProjects`
- `createProject`
- `getProjectStructure`
- `createSequence`

Discover live parameters with `clipit tools describe` or MCP `tools/list` instead of copying a remembered schema.

## Structure rules

- Name projects for the campaign, episode, or deliverable—not “New Project.”
- Use separate sequences for meaningfully different cuts, aspect ratios, or approval states.
- Do not duplicate a sequence merely to compensate for uncertain state; read it first.
- Set the active sequence before any implicit timeline command.
- Keep platform alternates clearly named and do not publish from the wrong version.

## Completion

A created project is ready for editing only when its returned sequence/tracks are visible in `getProjectStructure` and context points to the intended IDs. Project creation alone does not assemble, render, or deliver an edit.
