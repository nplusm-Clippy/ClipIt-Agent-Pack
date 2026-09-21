# ClipIt inside Hermes

This unified package contains the agent tools, all 18 canonical skills, a gateway bridge and the optional Desktop Control Room. It does not replace Hermes or install the unrelated ClipIt desktop executable.

## Compatibility and installation

Tested source: Hermes release `v2026.9.14`, commit `345cd2b057a452236de401d3534b8502a7465e8d`. That release reports runtime version `0.21.3`. The manifest checks the runtime version; the immutable tested commit is the stronger compatibility anchor.

The package uses manifest file format 1, supported by the released installer. Minimum Hermes version, Python dependencies, required secret, opt-in tools and capability declarations are retained. The pinned release's runtime accepts manifest format 2, but its Git installer rejects it; format 1 avoids that installer/runtime mismatch.

### Install version 3.1.0

Start from the intended Hermes profile. Add `--profile <your-profile>` to each `hermes` command when using a named profile; choose that same profile in Desktop. The default commands below use the current/default profile. Do not switch or restart unrelated gateways.

```bash
CLIPIT_RELEASE_SHA="$(git ls-remote --tags https://github.com/nplusm-Clippy/ClipIt-Agent-Pack.git \
  'refs/tags/v3.1.0' 'refs/tags/v3.1.0^{}' | awk 'NR == 1 { sha = $1 } /\^\{\}$/ { sha = $1 } END { print sha }')"
test "${#CLIPIT_RELEASE_SHA}" -eq 40 && \
  hermes plugins install nplusm-Clippy/ClipIt-Agent-Pack --ref "$CLIPIT_RELEASE_SHA" --no-enable
```

Compare the resolved commit with the [release record](https://github.com/nplusm-Clippy/ClipIt-Agent-Pack/releases/tag/v3.1.0). The tag must be published before these commands work. Hermes scans third-party code; review any caution findings before accepting its interactive confirmation. Never disable the scanner to install this pack.

Hermes reports Python dependencies but does not install them automatically. Install `requests>=2.32.0,<3` into the Python environment that runs your Hermes gateway. For the standard Hermes checkout:

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install 'requests>=2.32.0,<3'
hermes plugins enable clipit
hermes clipit doctor
```

If Hermes is installed elsewhere, use that installation's Python executable instead. This dependency setup is for the gateway, not the browser or another system Python.

1. Install the pinned package with the Python plugin initially disabled.
2. Configure `CLIPPER_API_KEY` through the hidden `requires_env` prompt in the gateway profile that will use ClipIt. Prefer a dedicated least-privilege key; an existing key retains its existing scope.
3. Enable the Python plugin: `hermes plugins enable clipit`.
4. Restart only the relevant gateway/Desktop backend when idle, then separately enable the Desktop extension under **Capabilities → Plugins** (called **Skills → Plugins** in some versions). The Tools tab shows eight Clipit tools; toggling a skill or toolset alone does not enable the Desktop extension.
5. Open ClipIt in the sidebar, inspect the account/workspace, credential label and permissions, then use **Connection → Diagnostics → Run Doctor**. The plugin is off by default.

The macOS Desktop 0.17.0 build used in the original acceptance had a host route-cache defect and required a narrow local compatibility patch. An unpatched 0.17.0 Desktop is not covered by that acceptance, and availability of a released Desktop build resolving that defect has not been verified. Use a compatible Desktop build verified to load extension routes; Python tools and portable skills remain usable without Desktop. Do not install an unrelated ClipIt desktop executable or overwrite Hermes core files as part of this package installation.

The Desktop Control Room needs the matching ClipIt server platform contract. When the server lacks it, the UI reports an upgrade requirement; legacy CLI/MCP/Python paths remain usable.

For a separate deployment, configure `CLIPPER_BASE_URL` and its exact hostname in `CLIPPER_ALLOWED_HOSTS` in the gateway environment. HTTP is rejected except explicit loopback development with `CLIPPER_ALLOW_LOCAL_HTTP=1`. No arbitrary URL proxy or redirects are accepted.

## Local and remote gateways

Python and `dashboard/plugin_api.py` run on the selected gateway. The Desktop `plugin.js` runs on the user's device. A remote setup therefore needs the same reviewed package version at both roots. Hermes' unified package installer owns the Desktop copy and package provenance. Do not manually overwrite another plugin or profile.

The credential lives on the gateway, never in renderer storage or composer attachments. Desktop uses the profile-aware `ctx.rest` door. A connection identifier binds requests to the current credential, so rotation requires a refresh before mutation. Choose local files on the Desktop device: the browser sends File/Blob data directly to the authorized storage URL, in bounded multipart chunks. A remote gateway path is not a path to a Desktop file.

Polling is authoritative when the server advertises tested coordinated polling. Otherwise the UI uses manual refresh. It does not assume OAuth remotes support plugin sockets. Disabling the plugin removes contributions, listeners and timers. In-flight network requests are bounded by their timeout; stale profile results are ignored.

## Tools and workflows

`clipit_status`, `clipit_discover`, `clipit_execute`, `clipit_orchestrate`, `clipit_runs`, `clipit_control_run`, `clipit_respond_to_approval` and `clipit_artifacts` route to the shared public API. Tool discovery is live; a compatible new server capability does not require rebuilding the pack. `/clipit doctor`, `/clipit-runs` and `/clipit-approvals` use the same adapters.

Read `clipit:clipit-operator` before editing. Native skills register from canonical `clipper/` source. Portable skill-only installs use the generated self-contained `skills/` directories; preserve existing legacy installs until their owner chooses to remove them.

From a terminal, `hermes clipit status` and `hermes clipit doctor` use the same runtime. Without Hermes, `python -m clipit_plugin --help` exposes the shared client directly.

Doctor reports the observed Python/Hermes runtime, public plugin registration, account permissions/spend limits, and a server-clock estimate with network uncertainty. Its optional legacy-skill check inspects only names in the active SDK-provided profile, skips symlinks and stops after 256 entries/depth three; possible duplicates are guidance, never automatically removed. Desktop SDK version and whether a client is local or remote are explicitly unknown when the gateway cannot observe them.

The Control Room offers source intake, run and event inspection, exact approvals, allowed controls, artifacts, live capability preflight and execution, and diagnostics. Approval is bound to the current run and action digest. A run receipt or provider completion is not delivery QA. Download requires the current selected export ID; stale edits are rejected by ClipIt.

## Recovery, rotation and removal

Every platform mutation requires a stable idempotency key. After a timeout, look up that original key. Never repeat the action through another transport to see whether it works. The UI saves only receipt identities in plugin-scoped storage, partitioned by account/credential/profile; prompts, credentials, payloads and signed URLs are not persisted there.

Definitive request rejection preserves its key without blocking later corrected requests. An uncertain response remains pending even when HTTP itself succeeded. An acknowledged asynchronous job is accepted, not completed. After restarting, look up a pending URL-import receipt, then use **Check imported video** to retrieve its source ID without starting another import.

Pause/cancel/resume are available only when the server permits the transition. Retry is restricted to a failure proven to have occurred before dispatch. Partial paid work requires reconciliation rather than automatic replay. Approval continuation receives a new run ID and retains parent lineage.

Rotate or revoke keys in ClipIt, update the gateway secret environment, restart/reload the relevant gateway profile if required by Hermes, and refresh the connection. Uninstalling the plugin does not revoke a key shared with the CLI or other harnesses.

Disable the Desktop plugin and run `hermes plugins disable clipit` before update/rollback. Install the reviewed replacement commit through Hermes with `--force --ref`, then rerun Doctor and the connection/read checks. Existing server jobs continue independently. An older UI must fail closed on unsupported protocol rather than reinterpreting new states. `hermes plugins remove clipit` removes the native package; remove receipt metadata or legacy skill copies only if you intend to, and preserve unrelated profiles/skills/plugins.

## Control Room 3.1

Activity is the default view: search work, filter Needs you/In progress/Finished, inspect its source and observed phase, and review recorded actions. Percentages supplied by the workflow are estimates and are not presented as measured completion. Outputs includes only resources explicitly recorded as workflow outputs; historical unclassified associations remain available in technical details.

New brief searches authorized named sources. Source and clip access still require the existing `video_processing` and `clip_generation` permissions. The additive `/agent/platform/resources` endpoint, optional `presentation` fields and structured events also work through the shared HTTP API and standalone Python bridge; no Hermes dependency was added to the server.

Approvals show exact supplied action fields and revalidate the current digest before submission. Pause/cancel show requested state until confirmed. Export review selects an exact export identity and refreshes temporary media links on demand. A change request is a local draft that can be copied or attached to the current Hermes composer; it never sends automatically or claims to control an unrelated session.

Advanced contains live tool schemas, connection diagnostics and a per-profile Classic interface switch for rollback. Polling uses one shared budget while the view is mounted, with slower checks while hidden; closing the view does not provide background monitoring. Unknown operation receipts continue to block new mutations until reconciled.

## Local verification

Use an isolated Python environment with `requirements.txt` plus `requirements-test.txt`:

```bash
python -m unittest discover -s tests -v
python tooling/build_portable_skills.py --check
npm ci --ignore-scripts
npm test
python tooling/build_parity_inventory.py --check
python tooling/package_release.py --output dist
python -m zipfile -e dist/clipit-agent-pack-3.1.0.zip dist/extracted
hermes plugins doctor dist/extracted/clipit --ci
python tooling/verify_hermes_install.py --hermes-source /path/to/pinned/hermes-agent
```

Hermes Doctor is run against the actual pinned source, not the fixture extractor used by portable skill tests. The clean installer check runs Hermes' Git installer in a disposable home, retains opt-in and version gates, and checks every portable skill through its real GitHub parser, scanner, quarantine and installer. Git and file-download transports use the local candidate snapshot; a public post-publication install remains a separate release check. It reports caution findings rather than disabling scanners. No test should use a production credential or execute paid generation, publishing or payment. Native Desktop acceptance, remote gateway acceptance, staging media flows and the mixed-client soak remain release gates until their evidence is recorded.

## Troubleshooting and release configuration

- Missing permissions: inspect Settings/Doctor and the live catalog. `clippy_agent` is required for platform operations; source import also requires `url_extraction`. Each tool enforces its own additional permissions and current spend limits.
- Unknown operation outcome: use the original receipt key. A malformed response or lost connection after a mutation is uncertain; it does not authorize a new request key.
- Credential/profile switch: refresh before acting. In-flight results from the previous scope are discarded; upload sessions cannot store a checkpoint or dispatch another part in the new scope.
- A saved upload checkpoint belongs to one exact file. Select that original file to resume. The explicit local checkpoint reset affects only local metadata; use the separate abort action to cancel an active server upload.
- A shared polling cooldown is normal. The same key can be used by other harnesses, and rejected contenders honor the server delay. Manual reads and unrelated clients retain quota headroom.
- Plugin disable removes Desktop listeners/timers and agent registrations. The agent unload hook clears the same-package gateway connection pool when both surfaces share a process. Hermes' own request-time gate blocks a disabled gateway plugin; gateway shutdown also clears its pool. Already dispatched server work continues independently.

After staging acceptance and publication, configure `CLIPIT_AGENT_PACK_RELEASE_SHA` on the ClipIt server with the reviewed full 40-character Agent Pack commit. Generated Hermes onboarding will then advertise that immutable native install and correct portable bundle commands. Until configured, onboarding uses the existing CLI path and explicitly says the native release is not advertised. Other harness setup text is unchanged.

Core navigation and overview labels use Hermes plugin locale bundles (English and Spanish); detailed workflow/diagnostic copy currently falls back to English. No animation is required to understand state. Actual screen-reader, narrow-window, theme and operating-system acceptance remains part of the release matrix.
