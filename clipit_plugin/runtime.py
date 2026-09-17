from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from importlib import metadata
from itertools import islice
from pathlib import Path
from uuid import uuid4

from .client import ClipItClient, ClipItError, Settings
from .version import CONTRACT_VERSION, HERMES_MINIMUM, HERMES_TESTED_COMMIT, VERSION


def _clock_check(server_time, wall_start, wall_end, elapsed):
    unknown = {"status": "unknown", "serverAheadMs": None, "uncertaintyMs": None, "thresholdMs": 30000}
    try:
        if not isinstance(server_time, str) or len(server_time) > 64:
            raise ValueError()
        timestamp = datetime.fromisoformat(server_time.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError()
        if abs(wall_end - wall_start - elapsed) > 1 or elapsed < 0:
            return {**unknown, "reason": "Local clock changed during measurement."}
        uncertainty = max(1, round(elapsed * 500))
        offset = round((timestamp.timestamp() - (wall_start + wall_end) / 2) * 1000)
        status = "unknown" if uncertainty > 30000 else "skew" if abs(offset) > 30000 + uncertainty else "ok"
        return {"status": status, "serverAheadMs": offset, "uncertaintyMs": uncertainty, "thresholdMs": 30000,
                "reason": "Estimate from server time and request midpoint; positive means the server clock is ahead."}
    except (ValueError, OverflowError, OSError):
        return {**unknown, "reason": "The server did not provide a valid timezone-aware time."}


def _hermes_identity():
    loaded = getattr(sys.modules.get("hermes_cli"), "__version__", None)
    if isinstance(loaded, str) and re.fullmatch(r"[A-Za-z0-9.+_-]{1,64}", loaded):
        return {"version": loaded, "source": "loaded hermes_cli"}
    try:
        version = metadata.version("hermes-agent")
        if re.fullmatch(r"[A-Za-z0-9.+_-]{1,64}", version):
            return {"version": version, "source": "installed hermes-agent distribution"}
    except metadata.PackageNotFoundError:
        pass
    return {"version": None, "source": "unknown; Hermes runtime is not observable"}


def _legacy_skill_check():
    result = {"status": "unknown", "possibleDuplicates": [], "entriesChecked": 0, "truncated": False,
              "coverage": "Active Hermes profile skills only; project and external skill roots are not inspected."}
    provider = getattr(sys.modules.get("hermes_constants"), "get_hermes_home", None)
    if not callable(provider):
        return {**result, "reason": "Hermes profile path is not available from the loaded SDK."}
    try:
        root = Path(provider()) / "skills"
        if root.is_symlink():
            return {**result, "reason": "The skills root is a symlink; no scan performed."}
        if not root.exists():
            return {**result, "status": "checked"}
        names = {path.name for path in islice((Path(__file__).resolve().parents[1] / "clipper").iterdir(), 64) if path.is_dir()}
        names.update({"clipper", "clipit", "clippy"})
        pending = [(root, 0)]
        while pending:
            directory, depth = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    if result["entriesChecked"] >= 256:
                        return {**result, "status": "partial", "truncated": True}
                    result["entriesChecked"] += 1
                    if entry.name.startswith(".") or not entry.is_dir(follow_symlinks=False):
                        continue
                    path = Path(entry.path)
                    skill = path / "SKILL.md"
                    if entry.name in names and not skill.is_symlink() and skill.is_file():
                        result["possibleDuplicates"].append(entry.name)
                    elif depth < 2:
                        pending.append((path, depth + 1))
        return {**result, "status": "checked", "possibleDuplicates": sorted(result["possibleDuplicates"])}
    except (OSError, TypeError, ValueError):
        return {**result, "status": "partial" if result["entriesChecked"] else "unknown",
                "reason": "The bounded skill-directory check could not finish; no files were changed."}


class Runtime:
    def __init__(self, settings_factory=Settings.from_environment, client_factory=ClipItClient, *, registration=None):
        self.settings_factory, self.client_factory = settings_factory, client_factory
        self._lock = threading.RLock()
        self._client = None
        self._scope = None
        self._closed = False
        self._instance_id = str(uuid4())
        self._registration = {key: value if isinstance(value, str) else None for key, value in registration.items()} if isinstance(registration, dict) else None
        self.requests, self.failures = 0, 0

    def close(self):
        with self._lock:
            self._closed = True
            if self._client:
                self._client.close()
            self._client, self._scope = None, None

    def reset(self):
        with self._lock:
            if self._client:
                self._client.close()
            self._client, self._scope = None, None

    def call(self, operation, arguments=None, *, media=False, connection_id=None):
        settings = self.settings_factory()
        if connection_id is not None and settings.scope != connection_id:
            raise ClipItError("CONNECTION_CHANGED", "The gateway credential changed. Refresh and review this action in the current account.", 409)
        with self._lock:
            if self._closed:
                raise ClipItError("PLUGIN_DISABLED", "The ClipIt plugin was disabled.", 503)
            if settings.scope != self._scope:
                if self._client:
                    self._client.close()
                self._client, self._scope = self.client_factory(settings), settings.scope
            client = self._client
            self.requests += 1
        try:
            return client.call(operation, arguments, media=media)
        except ClipItError:
            with self._lock:
                self.failures += 1
            raise

    def status(self):
        settings = self.settings_factory()
        identity = self.call("identity", connection_id=settings.scope)
        wall_start, mono_start = time.time(), time.monotonic()
        try:
            compatibility = self.call("compatibility", connection_id=settings.scope)
        except ClipItError as exc:
            if exc.status != 404:
                raise
            compatibility = {"contractVersion": None, "features": {}, "upgradeRequired": True}
        clock = _clock_check(compatibility.get("serverTime"), wall_start, time.time(), time.monotonic() - mono_start)
        key = identity.get("apiKey", {})
        return {"connected": True, "pluginVersion": VERSION, "contractVersion": CONTRACT_VERSION,
                "connectionId": settings.scope,
                "appOrigin": settings.base_url,
                "scope": identity.get("scope"), "accountId": identity.get("user", {}).get("id"),
                "credentialId": key.get("id"), "permissions": key.get("permissions", {}),
                "rateLimit": key.get("rateLimit"), "spendLimits": key.get("spendLimits"),
                "compatibility": compatibility, "clock": clock}

    def doctor(self):
        started = time.monotonic()
        try:
            connection = self.status()
        except ClipItError as exc:
            connection = exc.public()
        return {"pluginVersion": VERSION, "contractVersion": CONTRACT_VERSION,
                "testedHermesCommit": HERMES_TESTED_COMMIT, "minimumHermes": HERMES_MINIMUM,
                "runtime": {"instanceId": self._instance_id, "pluginName": "clipit", "codeVersion": VERSION,
                            "registration": dict(self._registration) if self._registration is not None else None,
                            "pythonVersion": ".".join(str(value) for value in sys.version_info[:3]),
                            "pythonImplementation": sys.implementation.name, "hermes": _hermes_identity()},
                "clock": connection.get("clock", {"status": "unknown", "reason": "Connection unavailable."}),
                "desktop": {"version": None, "status": "unknown", "reason": "Gateway diagnostics cannot observe the Desktop SDK version."},
                "topology": {"mode": "unknown", "reason": "A gateway cannot determine whether its Desktop client is local or remote."},
                "legacySkills": _legacy_skill_check(),
                "connection": connection, "elapsedMs": round((time.monotonic() - started) * 1000),
                "requests": self.requests, "failures": self.failures,
                "authMode": "gateway-profile-environment", "automaticMutationRetries": False,
                "polling": "negotiated from compatibility; manual when unavailable",
                "supportData": "No credentials, prompts, transcripts or media URLs are included."}

    def tool(self, name, args):
        if not isinstance(args, dict):
            raise ClipItError("INVALID_INPUT", "Tool arguments must be an object.")
        if name == "clipit_status":
            return self.doctor() if args.get("doctor") else self.status()
        if name == "clipit_discover":
            operation = args.get("kind", "catalog")
            if operation not in {"catalog", "tool", "manifest", "tools", "skills", "skill", "recipes", "media_guides", "media_guide"}:
                raise ClipItError("INVALID_INPUT", "Unsupported discovery kind.")
            return self.call(operation, {"id": args.get("id"), "query": args.get("query", {})})
        if name in {"clipit_execute", "clipit_orchestrate"}:
            operation = "preflight" if args.get("preflight") else ("execute" if name == "clipit_execute" else "orchestrate")
            body = {key: args[key] for key in ("request", "idempotencyKey", "preflightId") if key in args}
            return self.call(operation, {"body": body})
        if name == "clipit_runs":
            operation = args.get("view", "runs")
            if operation not in {"runs", "run", "events", "operation", "overview"}:
                raise ClipItError("INVALID_INPUT", "Unsupported run view.")
            return self.call(operation, {"id": args.get("id"), "query": args.get("query", {})})
        if name in {"clipit_control_run", "clipit_respond_to_approval"}:
            body = {key: value for key, value in args.items() if key != "runId"}
            return self.call("control" if name == "clipit_control_run" else "approval", {"id": args.get("runId"), "body": body})
        if name == "clipit_artifacts":
            operation = args.get("view", "artifacts")
            if operation not in {"artifacts", "library", "delivery_state"}:
                raise ClipItError("INVALID_INPUT", "Unsupported artifact view.")
            return self.call(operation, {"id": args.get("id"), "query": args.get("query", {})})
        raise ClipItError("UNKNOWN_TOOL", "Unknown ClipIt tool.")

    def tool_json(self, name, args):
        try:
            return json.dumps(self.tool(name, args), ensure_ascii=False)
        except ClipItError as exc:
            return json.dumps(exc.public(), ensure_ascii=False)
        except Exception:
            return json.dumps({"ok": False, "error": {"code": "PLUGIN_ERROR", "message": "ClipIt plugin could not complete the request. Run /clipit doctor for redacted diagnostics."}})
