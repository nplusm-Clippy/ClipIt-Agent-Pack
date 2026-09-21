from pathlib import Path
import sys

from .runtime import Runtime


def _schema(name, description, properties, required=()):
    return {"name": name, "description": description, "parameters": {
        "type": "object", "properties": properties, "required": list(required), "additionalProperties": False}}


_ID = {"type": "string", "minLength": 1, "maxLength": 128}
_KEY = {"type": "string", "minLength": 8, "maxLength": 128,
        "description": "Stable caller-generated operation key. After disconnection, look it up with clipit_runs view=operation before retrying."}
_QUERY = {"type": "object", "description": "Bounded discovery filters or cursor/limit (maximum 100, events 250)."}
_REQUEST = {"type": "object", "description": "Public ClipIt request from the live tool schema. All permissions, approvals, spend caps and resource exactness remain server-enforced."}
TOOL_SCHEMAS = [
    _schema("clipit_status", "Inspect ClipIt connection, permissions, spending caps and protocol support. No secrets returned.", {"doctor": {"type": "boolean"}}),
    _schema("clipit_discover", "Read the compact live catalog first, then kind=tool with its name for one full schema. Discover operating guides before execution. Load clipit:clipit-operator for editorial workflow.", {
        "kind": {"type": "string", "enum": ["catalog", "tool", "manifest", "tools", "skills", "skill", "recipes", "media_guides", "media_guide"]}, "id": _ID, "query": _QUERY}),
    _schema("clipit_execute", "Preflight or execute a discovered ClipIt tool. Use preflight first; obtain explicit approval for paid, destructive or publishing actions. Never repeat an uncertain mutation through another transport.", {
        "request": _REQUEST, "idempotencyKey": _KEY, "preflight": {"type": "boolean"}, "preflightId": _ID}, ["request"]),
    _schema("clipit_orchestrate", "Start a durable Clippy workflow using userMessage and optional stable video/clip/project/sequence IDs. Receipt is not completion; inspect runs and approvals.", {
        "request": _REQUEST, "idempotencyKey": _KEY}, ["request", "idempotencyKey"]),
    _schema("clipit_runs", "Read ClipIt runs, details, events, overview or the outcome of an original idempotency key. Preserve partial artifacts and exact next gate.", {
        "view": {"type": "string", "enum": ["runs", "run", "events", "operation", "overview"]}, "id": _ID, "query": _QUERY}),
    _schema("clipit_control_run", "Control an owned run only when its allowedControls permits the action. Retry may require reconciliation to avoid duplicating paid work.", {
        "runId": _ID, "idempotencyKey": _KEY, "action": {"type": "string", "enum": ["pause", "resume", "cancel", "retry"]}, "expectedStatus": {"type": "string"}}, ["runId", "idempotencyKey", "action", "expectedStatus"]),
    _schema("clipit_respond_to_approval", "Submit the user's explicit decision for the exact current run approval and actionDigest. Never infer approval or substitute another pending approval.", {
        "runId": _ID, "approvalId": _ID, "idempotencyKey": _KEY,
        "decision": {"type": "string", "enum": ["approved", "cancelled"]}, "actionDigest": {"type": "string", "pattern": "^[a-f0-9]{64}$"}}, ["runId", "approvalId", "idempotencyKey", "decision", "actionDigest"]),
    _schema("clipit_artifacts", "Read stable run artifacts, library or exact clip delivery readiness. Provider completion is not applied, QA-passed or current export evidence.", {
        "view": {"type": "string", "enum": ["artifacts", "library", "delivery_state"]}, "id": _ID, "query": _QUERY}),
]


def register(ctx):
    manifest = getattr(ctx, "manifest", None)
    registration = {"pluginId": getattr(ctx, "plugin_id", None), "manifestName": getattr(manifest, "name", None),
                    "manifestVersion": getattr(manifest, "version", None)}
    registration = {key: value if isinstance(value, str) and len(value) <= 128 else None for key, value in registration.items()}
    runtime = Runtime(registration=registration)
    def unload():
        runtime.close()
        bridge = sys.modules.get("hermes_dashboard_plugin_clipit")
        if bridge and Path(getattr(bridge, "__file__", "")).resolve() == Path(__file__).resolve().parents[1] / "dashboard" / "plugin_api.py":
            bridge.runtime.reset()
    ctx.on_unload(unload)
    for schema in TOOL_SCHEMAS:
        name = schema["name"]
        def handler(args, _name=name, **_kwargs):
            return runtime.tool_json(_name, args)
        ctx.register_tool(name=name, toolset="clipit", schema=schema, handler=handler,
                          description=schema["description"], requires_env=["CLIPPER_API_KEY"], override=False)
    root = Path(__file__).resolve().parents[1]
    for path in sorted((root / "clipper").glob("*/SKILL.md")):
        ctx.register_skill(name=path.parent.name, path=path,
                           description="ClipIt " + path.parent.name.replace("-", " "))
    ctx.register_command("clipit", lambda args: runtime.tool_json("clipit_status", {"doctor": args.strip() == "doctor"}),
                         description="ClipIt connection and redacted diagnostics", args_hint="[doctor]")
    ctx.register_command("clipit-runs", lambda args: runtime.tool_json("clipit_runs", {"view": "run", "id": args.strip()} if args.strip() else {}),
                         description="Read ClipIt runs", args_hint="[run-id]")
    ctx.register_command("clipit-approvals", lambda _args: runtime.tool_json("clipit_runs", {"query": {"status": "awaiting_approval"}}),
                         description="Review ClipIt runs awaiting approval")
    def setup_cli(parser):
        parser.add_argument("action", choices=["status", "doctor"], nargs="?", default="status")
    def handle_cli(args):
        print(runtime.tool_json("clipit_status", {"doctor": args.action == "doctor"}))
    ctx.register_cli_command(name="clipit", help="ClipIt connection and redacted diagnostics",
                             setup_fn=setup_cli, handler_fn=handle_cli)
