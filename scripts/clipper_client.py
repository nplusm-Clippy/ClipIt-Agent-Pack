"""
Clipper REST client shared by all skill scripts.

Reads the active ClipIt CLI profile plus CLIPPER_API_KEY and CLIPPER_BASE_URL.
Named profiles are isolated from ambient personal key and base-URL settings.
Never logs the API key.
"""

import os
import sys
import json
import time
from pathlib import Path
import requests
from typing import Any, Dict, Optional, Tuple

DEFAULT_BASE_URL = "https://clipit.dev"


def _clipit_config_path() -> Path:
    config_dir = os.environ.get("CLIPIT_CONFIG_DIR")
    if config_dir:
        return Path(config_dir).expanduser() / "config.json"
    if os.name == "nt":
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / "ClipIt" / "config.json"
    return Path.home() / ".config" / "clipit" / "config.json"


def _read_clipit_config() -> Dict[str, Any]:
    config_path = _clipit_config_path()
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        return {}

    return config if isinstance(config, dict) else {}


def _profile_config(config: Dict[str, Any], profile_name: str) -> Dict[str, Any]:
    profiles = config.get("profiles")
    configured_profile = (
        profiles.get(profile_name) if isinstance(profiles, dict) else None
    )

    if profile_name != "default":
        return configured_profile if isinstance(configured_profile, dict) else {}

    profile: Dict[str, Any] = {}
    for field in ("apiKey", "baseUrl"):
        if field in config:
            profile[field] = config[field]
    if isinstance(configured_profile, dict):
        profile.update(configured_profile)
    return profile


def _non_empty_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def resolve_clipit_connection(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    profile: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Resolve a key, base URL, and profile using the ClipIt CLI contract."""
    config = _read_clipit_config()
    profile_name = (
        _non_empty_string(profile)
        or _non_empty_string(os.environ.get("CLIPIT_PROFILE"))
        or _non_empty_string(config.get("currentProfile"))
        or "default"
    )
    configured_profile = _profile_config(config, profile_name)

    resolved_key = _non_empty_string(api_key)
    if not resolved_key and profile_name != "default":
        resolved_key = _non_empty_string(configured_profile.get("apiKey"))
        if not resolved_key:
            raise RuntimeError(
                f'ClipIt profile "{profile_name}" does not contain an API key. '
                "Set the workspace key on that named profile. The ambient "
                "CLIPPER_API_KEY was not used."
            )
    if not resolved_key:
        resolved_key = _non_empty_string(os.environ.get("CLIPPER_API_KEY"))
    if not resolved_key:
        resolved_key = _non_empty_string(configured_profile.get("apiKey"))
    if not resolved_key:
        raise RuntimeError(
            "No ClipIt API key was found. Set CLIPPER_API_KEY, configure the "
            "default ClipIt CLI profile, or pass api_key explicitly."
        )

    resolved_base_url = _non_empty_string(base_url)
    if not resolved_base_url and profile_name != "default":
        resolved_base_url = (
            _non_empty_string(configured_profile.get("baseUrl"))
            or DEFAULT_BASE_URL
        )
    if not resolved_base_url:
        resolved_base_url = (
            _non_empty_string(os.environ.get("CLIPPER_BASE_URL"))
            or _non_empty_string(configured_profile.get("baseUrl"))
            or DEFAULT_BASE_URL
        )
    resolved_base_url = resolved_base_url.rstrip("/")
    return resolved_key, resolved_base_url, profile_name


def require_enterprise_workspace_scope(
    agent_identity: Any,
    expected_workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Require the authoritative active team-operated enterprise scope."""
    if not isinstance(agent_identity, dict) or "scope" not in agent_identity:
        raise RuntimeError(
            "ClipIt did not return an authoritative workspace scope. Update the "
            "server/Agent Pack before operating on enterprise content."
        )
    scope = agent_identity.get("scope")
    if not isinstance(scope, dict):
        raise RuntimeError("ClipIt returned an invalid workspace scope.")

    invalid_requirements = []
    if scope.get("identityType") != "workspace_api_key":
        invalid_requirements.append("identityType=workspace_api_key")
    if scope.get("enterprise") is not True:
        invalid_requirements.append("enterprise=true")
    if not _non_empty_string(scope.get("workspaceId")):
        invalid_requirements.append("a workspace ID")
    if not _non_empty_string(scope.get("workspaceName")):
        invalid_requirements.append("a workspace name")
    if scope.get("workspaceStatus") != "active":
        invalid_requirements.append("workspaceStatus=active")
    if scope.get("workspaceRole") != "team_operator":
        invalid_requirements.append("workspaceRole=team_operator")
    if scope.get("billingMode") != "enterprise_usage_only":
        invalid_requirements.append("billingMode=enterprise_usage_only")
    if invalid_requirements:
        raise RuntimeError(
            "Enterprise workspace identity preflight failed; required: "
            + ", ".join(invalid_requirements)
            + "."
        )

    expected_workspace_id = _non_empty_string(expected_workspace_id)
    if expected_workspace_id and scope.get("workspaceId") != expected_workspace_id:
        raise RuntimeError(
            "Enterprise workspace identity preflight failed: the authenticated "
            "key belongs to a different workspace."
        )
    return scope


class ClipperError(Exception):
    """Raised for API errors. Contains status code and parsed error response."""

    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"[{code}] {message}")


class ClipperClient:
    """
    Thin REST client for the Clipper API v1.

    Handles authentication, error parsing, and file uploads.
    Does NOT handle retries — long operations should be polled via wait_for_job.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        profile: Optional[str] = None,
    ):
        self.api_key, self.base_url, self.profile_name = resolve_clipit_connection(
            api_key=api_key,
            base_url=base_url,
            profile=profile,
        )

    def get_agent_identity(self) -> Dict[str, Any]:
        identity = self.get("/api/v1/agent/me")
        if not isinstance(identity, dict):
            raise RuntimeError("ClipIt returned an invalid agent identity response.")
        return identity

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "User-Agent": "ClipItAgentPack/1.0",
        }

    def _handle_response(self, response: requests.Response) -> Any:
        if response.status_code in (200, 201, 202, 204):
            if response.status_code == 204:
                return None
            return response.json()

        try:
            body = response.json()
            raise ClipperError(
                status_code=response.status_code,
                code=body.get("code", "UNKNOWN"),
                message=body.get("error", "Unknown error"),
                details=body.get("details"),
            )
        except (ValueError, KeyError):
            raise ClipperError(
                status_code=response.status_code,
                code="INVALID_RESPONSE",
                message=f"HTTP {response.status_code}: {response.text[:200]}",
            )

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        response = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=30,
        )
        return self._handle_response(response)

    def post(self, path: str, json_body: Optional[Dict[str, Any]] = None) -> Any:
        response = requests.post(
            f"{self.base_url}{path}",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=json_body,
            timeout=60,
        )
        return self._handle_response(response)

    def patch(self, path: str, json_body: Dict[str, Any]) -> Any:
        response = requests.patch(
            f"{self.base_url}{path}",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=json_body,
            timeout=30,
        )
        return self._handle_response(response)

    def delete(self, path: str) -> Any:
        response = requests.delete(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=30,
        )
        return self._handle_response(response)

    def upload_file(self, path: str, file_path: str, field_name: str = "file") -> Any:
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}{path}",
                headers={
                    "X-API-Key": self.api_key,
                    "Accept": "application/json",
                    "User-Agent": "ClipItAgentPack/1.0",
                },
                files={field_name: f},
                timeout=600,
            )
        return self._handle_response(response)

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: float = 3.0,
        timeout: float = 600.0,
        show_progress: bool = True,
    ) -> Dict[str, Any]:
        """Poll GET /api/v1/jobs/:jobId until status is terminal."""
        deadline = time.time() + timeout
        last_progress = -1
        while time.time() < deadline:
            job = self.get(f"/api/v1/jobs/{job_id}")
            status = job.get("status")
            progress = job.get("progress", 0)

            if show_progress and progress != last_progress:
                print(f"  [{status}] {progress}%", file=sys.stderr)
                last_progress = progress

            if status == "completed":
                return job
            if status == "failed":
                err = job.get("error") or {}
                raise ClipperError(
                    status_code=500,
                    code=err.get("code", "JOB_FAILED"),
                    message=err.get("message", "Job failed"),
                    details=err,
                )
            if status == "cancelled":
                raise ClipperError(500, "JOB_CANCELLED", "Job was cancelled")

            time.sleep(poll_interval)

        raise ClipperError(
            500, "JOB_TIMEOUT", f"Job {job_id} did not complete within {timeout}s"
        )

    def wait_for_export(
        self,
        job_id: str,
        poll_interval: float = 3.0,
        timeout: float = 600.0,
        show_progress: bool = True,
    ) -> Dict[str, Any]:
        """Poll GET /api/v1/exports/:jobId until status is terminal."""
        deadline = time.time() + timeout
        last_progress = -1
        while time.time() < deadline:
            job = self.get(f"/api/v1/exports/{job_id}")
            status = job.get("status")
            progress = job.get("progress", 0)

            if show_progress and progress != last_progress:
                print(f"  [{status}] {progress}%", file=sys.stderr)
                last_progress = progress

            if status == "completed":
                return job
            if status in ("failed", "error"):
                err = job.get("error") or {}
                if isinstance(err, dict):
                    raise ClipperError(
                        status_code=500,
                        code=err.get("code", "EXPORT_FAILED"),
                        message=err.get("message", "Export failed"),
                        details=err,
                    )
                raise ClipperError(500, "EXPORT_FAILED", str(err or "Export failed"))
            if status == "cancelled":
                raise ClipperError(500, "EXPORT_CANCELLED", "Export was cancelled")

            time.sleep(poll_interval)

        raise ClipperError(
            500, "EXPORT_TIMEOUT", f"Export {job_id} did not complete within {timeout}s"
        )


def print_json(obj: Any) -> None:
    """Pretty-print JSON to stdout (used by scripts for agent consumption)."""
    print(json.dumps(obj, indent=2, default=str))


def main_wrapper(fn):
    """Decorator for script main functions. Catches ClipperError and prints
    a clean error message to stderr, exits with code 1."""

    def wrapped():
        try:
            fn()
        except ClipperError as e:
            print(
                f"ERROR: {e.message} (code: {e.code}, status: {e.status_code})",
                file=sys.stderr,
            )
            if e.details:
                print(
                    f"Details: {json.dumps(e.details, indent=2, default=str)}",
                    file=sys.stderr,
                )
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nCancelled.", file=sys.stderr)
            sys.exit(130)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    return wrapped
