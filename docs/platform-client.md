# Shared ClipIt platform contract

Contract `2026-09-16` adds `/api/v1/agent/platform` alongside existing v1 agent routes. It is usable by REST, CLI scripts, MCP clients and Python without Hermes. No Hermes profile, session, runtime package or key type is required. Existing v1 schemas, statuses, approval routes and CLI/MCP behavior remain supported.

Authenticate with the normal ClipIt API key. Ownership follows the authenticated key principal and enterprise workspace; a local profile alias grants no authority. Reads remain `private, no-store` and mutations recheck current permissions and spend policy.

| Operation | Public path |
|---|---|
| Compatibility and limits | GET `/api/v1/agent/platform/compatibility` |
| Compact catalog / selected schema | GET `/api/v1/agent/platform/catalog`, `/tools/:name` |
| Shared snapshot polling | POST `/api/v1/agent/platform/poll` with `{runId?,cursor?,runIds?}` |
| Durable URL import | POST `/api/v1/agent/platform/sources/import` with `{idempotencyKey,url,title?}` |
| Bounded overview / recipes | GET `/api/v1/agent/platform/overview`, `/recipes` |
| Run list/detail | GET `/api/v1/agent/platform/runs`, `/runs/:id` |
| Incremental events / artifacts | GET `/api/v1/agent/platform/runs/:id/events`, `/artifacts` |
| Library | GET `/api/v1/agent/platform/library` |
| Read-only preflight | POST `/api/v1/agent/platform/preflight` with `{request}` |
| Durable execution | POST `/api/v1/agent/platform/execute` with `{idempotencyKey,request,preflightId?}` |
| Durable orchestration | POST `/api/v1/agent/platform/runs` with `{idempotencyKey,request}` |
| State-checked control | POST `/api/v1/agent/platform/runs/:id/control` with `{idempotencyKey,action,expectedStatus}` |
| Exact approval | POST `/api/v1/agent/platform/runs/:id/approval` with `{idempotencyKey,approvalId,decision,actionDigest}` |
| Original outcome | GET `/api/v1/agent/platform/operations/:idempotencyKey` |

`request` is the existing orchestration or direct-execute input. Discovery remains at `/api/v1/agent/tools`, `/skills`, `/skills/:id`, `/capability-manifest` and `/media-guides`. The OpenAPI document is the authoritative deployed schema.

Run/library pages default to 50 and cap at 100; event pages default to 100 and cap at 250. Follow `nextCursor` while `hasMore`; save `resumeCursor` for later event polling even when `hasMore` is false. A changed filter starts a fresh cursor. Expired cursors require resync, not a restart of the run. Older event history may be unavailable before the projection migration; inspect `historyAvailableFrom`.

Reuse an idempotency key only for the same operation and payload. A conflicting payload returns 409. The server persists a receipt before dispatch; reads of the original key distinguish accepted, running, completed, failed and unknown outcomes. Never automatically retry mutations. Receipt retention lasts while the server job exists; deletion removes its replay protection. Stable references survive in receipts; sensitive transient results and signed URLs do not. Refresh media through the authenticated exact delivery contracts.

The optional Python client is independent of Hermes:

```bash
python -m clipit_plugin status
python -m clipit_plugin runs --query '{"limit":50}'
python -m clipit_plugin run --id RUN_ID
python -m clipit_plugin operation --id ORIGINAL_OPERATION_KEY
python -m clipit_plugin preflight --body @- < preflight-request.json
```

It reads `CLIPPER_API_KEY` and `CLIPPER_BASE_URL`; non-default hosts require `CLIPPER_ALLOWED_HOSTS`. New CLI output is one JSON document, including errors; exit 13 means a mutation outcome is unknown. These semantics belong only to this new optional entrypoint. The 52 existing Python scripts and published ClipIt CLI preserve their prior arguments, stdout and exit meanings.

New automatic polling is enabled only when the deployed compatibility response advertises it. Read quotas, retries, page size and media-transfer limits are shared product constraints, not Hermes-specific authorization exceptions. Existing upload intents support direct signed PUT/multipart transfer and status/abort/recovery; do not buffer entire media files into JSON or base64.

## Performance and limits

Catalog summaries omit full schemas. Fetch one tool detail after selection; its catalog digest and permission revision identify the current metadata. Authenticated responses retain `private, no-store`. An ETag is diagnostic metadata, not permission to cache or skip revalidation; these endpoints do not currently return 304.

The poll endpoint returns the overview, an optional selected run and up to 100 incremental events, plus summaries for at most 50 specified run IDs. It returns the data in the admitted request; clients must not reserve a slot and issue follow-up reads. PostgreSQL coordinates all processes using the same normal key quota window. Background admissions consume at most 20% of that quota, capped at 12 per minute. Very small quotas disable automatic polling. A denied request returns 429 and a positive Retry-After without consuming normal quota. Arbitrary incoming denied HTTP attempts are not themselves bounded by this admission rule.

The native controller uses one coordinator for the Control Room, activity display and notifications. It respects server cadence and Retry-After, slows hidden windows to at least 60 seconds, backs off during outages, and stops on close/disable or a selected terminal run. A manual refresh obtains complete approval and delivery detail. Scoped credentials are always revalidated by the API.

Uploads persist an intent key, file identity and content hashes before transfer. Hashing uses buffers no larger than 8 MiB. Multipart resume verifies the same complete file and each skipped part; URLs and file content are never stored in plugin state. The server and storage provider continue to enforce size/type, ownership and multipart completion. Exact download uses the existing clip/export contract and a transient signed URL. Artifact associations alone do not establish QA or a current export.
