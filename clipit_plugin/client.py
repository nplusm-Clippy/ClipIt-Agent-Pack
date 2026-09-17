from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import threading
from dataclasses import dataclass
from contextlib import contextmanager
from urllib.parse import quote, urlsplit

import requests

from .version import CONTRACT_VERSION, VERSION

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REQUEST_BYTES = 64 * 1024
_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
_OPERATION_KEY = re.compile(r"^[a-zA-Z0-9_.:-]{8,128}$")
_SECRET_FIELD = re.compile(r"^(authorization|cookie|set.cookie|api.?key|access.?token|refresh.?token|client.?secret|code.?verifier|device.?code|password|storage.?key)$", re.I)
_SIGNED_URL = re.compile(r"(?:[?&](?:x-amz-|x-goog-|signature=|sig=|token=))", re.I)


class ClipItError(Exception):
    def __init__(self, code, message, status=400, *, request_id=None, retry_after=None, operation_key=None):
        super().__init__(message)
        self.code, self.status = code, status
        self.request_id, self.retry_after, self.operation_key = request_id, retry_after, operation_key

    def public(self):
        return {"ok": False, "error": {"code": self.code, "message": str(self),
                "requestId": self.request_id, "retryAfter": self.retry_after, "status": self.status,
                "idempotencyKey": self.operation_key,
                "outcomeUnknown": self.code == "OUTCOME_UNKNOWN"}}


def redact(value, secret="", *, media=False, depth=0):
    if depth > 18:
        return "[depth limit]"
    if isinstance(value, dict):
        return {str(k): "[redacted]" if _SECRET_FIELD.match(str(k)) and not isinstance(v, (dict, list)) else redact(v, secret, media=media, depth=depth + 1)
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secret, media=media, depth=depth + 1) for v in value]
    if isinstance(value, str):
        if secret:
            value = value.replace(secret, "[redacted]")
        value = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [redacted]", value)
        if not media and _SIGNED_URL.search(value):
            return "[temporary media URL; refresh to download]"
    return value


def identifier(value):
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ClipItError("INVALID_INPUT", "A valid resource identifier is required.")
    return quote(value, safe="")


def operation_identifier(value):
    if not isinstance(value, str) or not _OPERATION_KEY.fullmatch(value):
        raise ClipItError("INVALID_INPUT", "A valid original operation key is required.")
    return quote(value, safe="")


def validate_base_url(value, *, allow_local=False, allowed_hosts=()):
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ClipItError("INVALID_CONFIGURATION", "ClipIt base URL must be an origin without credentials, path, query or fragment.")
    local = host in ("localhost", "127.0.0.1", "::1")
    try:
        address = ipaddress.ip_address(host)
        if not address.is_global and not (allow_local and address.is_loopback):
            raise ClipItError("INVALID_CONFIGURATION", "Private and link-local ClipIt endpoints are not allowed.")
    except ValueError:
        pass
    if parsed.scheme != "https" and not (allow_local and local and parsed.scheme == "http"):
        raise ClipItError("INVALID_CONFIGURATION", "ClipIt requires HTTPS; local HTTP needs explicit development opt-in.")
    if host not in {"clipit.dev", *allowed_hosts} and not (allow_local and local):
        raise ClipItError("INVALID_CONFIGURATION", "Add this deployment hostname to CLIPPER_ALLOWED_HOSTS in the gateway environment.")
    if not host:
        raise ClipItError("INVALID_CONFIGURATION", "ClipIt hostname is required.")
    return value.rstrip("/")


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str

    @classmethod
    def from_environment(cls):
        env = os.environ
        key = env.get("CLIPPER_API_KEY", "").strip()
        if not key or any(c in key for c in "\r\n"):
            raise ClipItError("NOT_CONNECTED", "Configure CLIPPER_API_KEY in this Hermes gateway profile's secret environment.", 401)
        return cls(validate_base_url(env.get("CLIPPER_BASE_URL", "https://clipit.dev"),
                   allow_local=env.get("CLIPPER_ALLOW_LOCAL_HTTP") == "1",
                   allowed_hosts=tuple(h.strip().lower() for h in env.get("CLIPPER_ALLOWED_HOSTS", "").split(",") if h.strip())), key)

    @property
    def scope(self):
        return hashlib.sha256((self.base_url + "\0" + self.api_key).encode()).hexdigest()


_GET = {
    "identity": "/agent/me", "compatibility": "/agent/platform/compatibility",
    "catalog": "/agent/platform/catalog", "overview": "/agent/platform/overview", "recipes": "/agent/platform/recipes",
    "tools": "/agent/tools", "skills": "/agent/skills", "manifest": "/agent/capability-manifest",
    "media_guides": "/agent/media-guides", "runs": "/agent/platform/runs",
    "library": "/agent/platform/library", "videos": "/videos", "resources": "/agent/platform/resources",
}
_RESOURCE_GET = {
    "tool": "/agent/platform/tools/{id}", "run": "/agent/platform/runs/{id}", "events": "/agent/platform/runs/{id}/events",
    "artifacts": "/agent/platform/runs/{id}/artifacts", "operation": "/agent/platform/operations/{id}",
    "skill": "/agent/skills/{id}", "media_guide": "/agent/media-guides/{id}",
    "upload_status": "/videos/uploads/{id}", "video": "/videos/{id}", "job": "/jobs/{id}",
    "delivery_state": "/clips/{id}/delivery-state", "download": "/clips/{id}/download",
}
_POST = {"orchestrate": "/agent/platform/runs", "execute": "/agent/platform/execute",
         "preflight": "/agent/platform/preflight", "upload_create": "/videos/uploads",
         "import_url": "/agent/platform/sources/import", "poll_budget": "/agent/platform/poll"}
_RESOURCE_POST = {"control": "/agent/platform/runs/{id}/control",
                  "approval": "/agent/platform/runs/{id}/approval",
                  "upload_parts": "/videos/uploads/{id}/parts", "upload_complete": "/videos/uploads/{id}/complete"}
OPERATIONS = frozenset(_GET) | frozenset(_RESOURCE_GET) | frozenset(_POST) | frozenset(_RESOURCE_POST) | {"upload_abort"}
_QUERY = {
    "runs": {"limit", "cursor", "status", "search"}, "events": {"limit", "cursor"},
    "artifacts": {"limit", "cursor", "kind", "status", "role", "readiness", "search"},
    "library": {"limit", "cursor", "kind", "status", "search", "role", "readiness"},
    "resources": {"limit", "cursor", "kind", "search"},
    "tools": {"skill", "category"}, "operation": {"operation"}, "videos": {"limit", "offset"},
    "delivery_state": {"exportId"}, "download": {"exportId"},
}


def operation_request(operation, arguments):
    if operation not in OPERATIONS:
        raise ClipItError("UNKNOWN_OPERATION", "This bridge operation is not supported.", 404)
    if not isinstance(arguments, dict) or set(arguments) - {"id", "query", "body"}:
        raise ClipItError("INVALID_INPUT", "Use only id, query and body for an allowlisted operation.")
    query, body = arguments.get("query", {}), arguments.get("body", {})
    if not isinstance(query, dict) or set(query) - _QUERY.get(operation, set()):
        raise ClipItError("INVALID_INPUT", "Unsupported query parameters.")
    if any(not isinstance(v, (str, int, bool)) or len(str(v)) > 1024 for v in query.values()):
        raise ClipItError("INVALID_INPUT", "Invalid query value.")
    if "limit" in query:
        maximum = 250 if operation == "events" else 100
        if not str(query["limit"]).isdigit() or not 1 <= int(query["limit"]) <= maximum:
            raise ClipItError("INVALID_INPUT", f"Page size must be between 1 and {maximum}.")
    if not isinstance(body, dict) or len(json.dumps(body).encode()) > MAX_REQUEST_BYTES:
        raise ClipItError("INVALID_INPUT", "Request body must be a bounded JSON object.")
    if operation in _GET:
        method, path = "GET", _GET[operation]
    elif operation in _RESOURCE_GET:
        method, path = "GET", _RESOURCE_GET[operation].format(id=operation_identifier(arguments.get("id")) if operation == "operation" else identifier(arguments.get("id")))
    elif operation in _POST:
        method, path = "POST", _POST[operation]
    elif operation in _RESOURCE_POST:
        method, path = "POST", _RESOURCE_POST[operation].format(id=identifier(arguments.get("id")))
    else:
        method, path = "DELETE", "/videos/uploads/" + identifier(arguments.get("id"))
    if method == "GET" and body:
        raise ClipItError("INVALID_INPUT", "Read operations do not accept a body.")
    if operation in {"execute", "orchestrate", "control", "approval", "import_url", "upload_create"}:
        key = body.get("idempotencyKey")
        if not isinstance(key, str) or not _OPERATION_KEY.fullmatch(key):
            raise ClipItError("IDEMPOTENCY_REQUIRED", "Supply a stable idempotencyKey and reuse it for outcome lookup after disconnection.")
    if operation in {"execute", "orchestrate", "preflight"} and not isinstance(body.get("request"), dict):
        raise ClipItError("INVALID_INPUT", "A request object is required.")
    if operation == "control" and body.get("action") not in {"pause", "resume", "cancel", "retry"}:
        raise ClipItError("INVALID_INPUT", "Unsupported run control.")
    if operation == "approval":
        if body.get("decision") not in {"approved", "cancelled"} or not re.fullmatch(r"[a-f0-9]{64}", str(body.get("actionDigest", ""))):
            raise ClipItError("INVALID_INPUT", "Use the current approval digest and approved or cancelled decision.")
        identifier(body.get("approvalId"))
    return method, "/api/v1" + path, query, body


class ClipItClient:
    def __init__(self, settings, session=None):
        self.settings = settings
        self.session = session or requests.Session()
        self.session.trust_env = False
        self._slots = threading.BoundedSemaphore(2)
        adapter = requests.adapters.HTTPAdapter(pool_connections=2, pool_maxsize=2, max_retries=0, pool_block=True)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def close(self):
        self.session.close()

    @contextmanager
    def _slot(self):
        if not self._slots.acquire(timeout=1):
            raise ClipItError("CLIENT_BUSY", "ClipIt already has two requests in progress. Retry after they finish.", 429, retry_after=1)
        try:
            yield
        finally:
            self._slots.release()

    def call(self, operation, arguments=None, *, media=False):
        method, path, query, body = operation_request(operation, arguments or {})
        operation_key = body.get("idempotencyKey")
        mutation = method != "GET" and operation not in {"preflight", "poll_budget"}
        attempts = 2 if method == "GET" else 1
        with self._slot():
            for attempt in range(attempts):
                try:
                    with self.session.request(method, self.settings.base_url + path, params=query,
                         json=body if method != "GET" else None,
                         headers={"Authorization": "Bearer " + self.settings.api_key,
                                  "Accept": "application/json", "User-Agent": "ClipIt-Agent-Pack/" + VERSION,
                                  "X-ClipIt-Contract": CONTRACT_VERSION},
                         timeout=(5, 60 if method != "GET" else 20), allow_redirects=False, stream=True) as response:
                        request_id = response.headers.get("X-Request-Id")
                        if 300 <= response.status_code < 400:
                            raise ClipItError("OUTCOME_UNKNOWN" if mutation else "REDIRECT_BLOCKED", "ClipIt redirected the request; check the configured deployment.", 502, request_id=request_id, operation_key=operation_key)
                        if "application/json" not in response.headers.get("Content-Type", "").lower():
                            if method == "GET" and response.status_code >= 400:
                                raise ClipItError("UPSTREAM_HTTP_ERROR", "ClipIt rejected this read request.", response.status_code, request_id=request_id)
                            raise ClipItError("OUTCOME_UNKNOWN" if mutation else "INVALID_RESPONSE", "ClipIt returned a non-JSON response.", 502, request_id=request_id, operation_key=operation_key)
                        chunks, size = [], 0
                        for chunk in response.iter_content(65536):
                            size += len(chunk)
                            if size > MAX_RESPONSE_BYTES:
                                raise ClipItError("OUTCOME_UNKNOWN" if mutation else "RESPONSE_TOO_LARGE", "ClipIt response exceeds the limit; use a smaller page.", 502, request_id=request_id, operation_key=operation_key)
                            chunks.append(chunk)
                        try:
                            payload = json.loads(b"".join(chunks))
                        except (ValueError, UnicodeError):
                            raise ClipItError("OUTCOME_UNKNOWN" if mutation else "INVALID_RESPONSE", "ClipIt returned invalid JSON.", 502, request_id=request_id, operation_key=operation_key) from None
                        if not isinstance(payload, (dict, list)):
                            raise ClipItError("OUTCOME_UNKNOWN" if mutation else "INVALID_RESPONSE", "ClipIt response must be a JSON object or array.", 502, request_id=request_id, operation_key=operation_key)
                        if response.status_code >= 400:
                            outer = payload if isinstance(payload, dict) else {}
                            error = outer.get("error", outer)
                            error = error if isinstance(error, dict) else {"message": str(error)}
                            request_id = request_id or outer.get("requestId")
                            delay = response.headers.get("Retry-After", "")
                            raise ClipItError("OUTCOME_UNKNOWN" if mutation and response.status_code >= 500 else str(error.get("code", outer.get("code", "UPSTREAM_ERROR")))[:128],
                                redact(str(error.get("message", "ClipIt rejected this request."))[:2000], self.settings.api_key),
                                response.status_code, request_id=request_id,
                                retry_after=min(300, max(1, int(delay))) if delay.isdigit() else None, operation_key=operation_key)
                        shape_ok = isinstance(payload, dict)
                        if operation in {"runs", "library", "events", "artifacts", "recipes", "catalog"}:
                            shape_ok = shape_ok and isinstance(payload.get("items"), list)
                        elif operation == "identity":
                            shape_ok = shape_ok and isinstance(payload.get("user"), dict) and isinstance(payload.get("apiKey"), dict)
                        elif operation == "tools":
                            shape_ok = shape_ok and isinstance(payload.get("tools"), list)
                        if not shape_ok:
                            raise ClipItError("OUTCOME_UNKNOWN" if mutation else "INVALID_RESPONSE", "ClipIt returned an incompatible response shape.", 502, request_id=request_id, operation_key=operation_key)
                        return redact(payload, self.settings.api_key, media=media)
                except requests.RequestException:
                    if attempt + 1 < attempts:
                        continue
                    raise ClipItError("OUTCOME_UNKNOWN" if mutation else "UPSTREAM_UNAVAILABLE",
                        "ClipIt could not be reached." if not mutation else "Connection lost. Look up this operation key before retrying; the action may already have started.",
                        503, operation_key=operation_key) from None
