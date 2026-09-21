# Developing the Agent Pack

Canonical editorial skills live in `clipper/`; the 52 executable Python scripts and eight support modules retain their existing behavior. Edit those sources only when that consumer change is intentional, then regenerate `skills/` with `tooling/build_portable_skills.py` and the parity inventory with `tooling/build_parity_inventory.py`.

The optional native implementation lives in `clipit_plugin/`, `dashboard/` and `desktop/`. Shared product rules belong in ClipIt's public API. Keep Hermes imports out of the standalone Python client and all application execution/billing code. Native registration must perform no network requests or user-state mutations. The gateway bridge accepts an allowlisted operation, never a caller-provided URL, method or credential.

Use the exact Hermes source revision in `agent-pack.manifest.json` for compatibility checks. Run the unit suite, portable-bundle check, parity check and npm tests. Build the archive twice and compare its hash, then run the real Hermes Doctor and lifecycle checks against the extracted archive. `.github/workflows/validate.yml` automates these offline gates; a local run does not prove CI ran.

Fixtures under `tests/fixtures/platform-responses.json` come from ClipIt's actual routes in disposable PostgreSQL with synthetic accounts and mocked provider dispatch. Refresh them from the corresponding application tests when the negotiated contract changes. Frozen published CLI tests and the original Agent Pack tests are separate compatibility gates and must not be rewritten to approve an accidental regression.

Never attach credentials, signed URLs, private prompts or media to issue reports. Supply the plugin/contract versions, tested Hermes revision, request/operation/run IDs, selected environment and redacted Doctor output. Distinguish operation acceptance, provider completion, applied state, QA, exact export and publish readiness.

Release order is server migration and additive API, isolated staging acceptance, accepted Agent Pack commit, deterministic artifact/checksum, then the server's reviewed install SHA. Native rollback disables or replaces only ClipIt-owned adapter files; existing public clients and shared jobs remain available. Staging/production mutations, publication, paid generation and publishing require their existing authorization.
