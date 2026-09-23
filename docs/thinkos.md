# Connect ClipIt to ThinkOS

Use the **ThinkOS** option on [ClipIt's Agents page](https://clipit.dev/agents) to get a prompt for your account and selected API host. This guide explains the host setup behind that prompt. ThinkOS uses ClipIt's existing CLI and local stdio MCP bridge; it does not require the native Hermes plugin or a separate ClipIt adapter. ClipIt does not provide a hosted HTTP MCP URL.

1. In ThinkOS, inspect `thinkos_cli` account, secret, and MCP help. Select or create a personal ClipIt account. Store your ClipIt API key through ThinkOS's protected secret input. Keep the ThinkOS account ID and secret ID as references; neither is the API key. Do not put the key in chat, command arguments, a config file, or logs.
2. Ensure the ThinkOS MCP **host** can launch the official `@clipit-ai/cli` at version `0.3.0` or newer. Use an existing host-visible `clipit` executable or install `@clipit-ai/cli@latest` in an isolated host runtime. An agent without a general shell may still ask ThinkOS to launch `npx --yes @clipit-ai/cli@latest` if the MCP host has Node.js and package access. If the host cannot launch either command, report that missing capability; cloning this repository alone does not install an MCP server.
3. Configure a **local stdio** MCP connection for the selected ThinkOS account. Set the command to the host-visible `clipit` executable and the arguments to `--base-url https://clipit.dev mcp stdio`. Bind the protected ThinkOS secret to the child process's `CLIPPER_API_KEY` environment variable. For a host using `npx`, put `--yes @clipit-ai/cli@latest` before those ClipIt arguments. Use a custom API host only when you explicitly trust that host.
4. Run `thinkos_cli mcp verify` and `thinkos_cli mcp tools list` for that account, then call the read-only `listUserVideos` tool. An empty video list still proves the call succeeded. Report the observed tool count and any missing permissions. A CLI version or auth check alone does not prove ThinkOS can use the connection. Do not use paid, publishing, or destructive calls as a setup test.

For an agent configuring the connection, the stdio registration should have these values (replace references with the selected ThinkOS records, **never** with a key literal):

```text
account: <ThinkOS ClipIt account ID>
transport: stdio
command: clipit
args: ["--base-url", "https://clipit.dev", "mcp", "stdio"]
secret binding: [{"location":"env","name":"CLIPPER_API_KEY","secret":"<ThinkOS secret ID or label>"}]
```

ThinkOS's current MCP bridge exposes tools but does not show MCP resources. Read [`clipit-operator`](../clipper/clipit-operator/SKILL.md) for operating rules and load only the domain skill needed for the task. The [CLI bridge](../README.md#mcp) itself also supports read-only `clipit://` resources in clients that expose `resources/list` and `resources/read`. Use live ClipIt tool schemas, prices, permissions, and confirmation responses as authority. Keep one execution owner for each mutation.

If ThinkOS lists no tools, inspect its MCP verification result, host-visible executable path, Node/package availability, and secret binding. If the host cannot start local stdio but supports authenticated HTTP with protected secret injection, the existing [ClipIt agent API](https://clipit.dev/agents) is a separate fallback. If it supports neither, connection is blocked by host capability rather than an absent hosted MCP URL.
