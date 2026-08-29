# ClipIt Agent Pack

Read `AGENTS.md` in this directory; it applies to Claude Code exactly as written. Keep `clipper/clipit-operator/SKILL.md` active for every ClipIt task, then load the smallest relevant domain skill.

Claude Code specific: install ClipIt CLI `0.3.0` or newer, prefer `clipit login`, then run `clipit agent install claude` and `clipit agent doctor claude --json`. The generated credential-free connection bundle is permission-scoped from the authenticated server. Use `clipit skills manifest/describe`, `clipit media-guides list/describe`, `clipit tools list/describe`, Clippy workflows, or the progressive resources and tools exposed by `clipit mcp stdio` as directed by the operator skill; never place credentials in a skill file.
