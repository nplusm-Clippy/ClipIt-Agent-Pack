# Enterprise Exactness

This path is for ClipIt team operators working in contracted client workspaces. It is not ordinary personal-account guidance.

## Authority boundary

- Store one workspace key in one non-default named CLI profile.
- Never place a workspace key in shared `CLIPPER_API_KEY` state.
- A named or active non-default profile is authoritative and must not fall back to ambient personal credentials or base URLs.
- Before any client-content read or mutation, verify the expected workspace ID, active status, `team_operator` authority, and `enterprise_usage_only` billing.
- A successful personal library or video listing is not workspace proof.

```bash
clipit auth set-key --stdin --profile "enterprise-client-slug"
clipit auth use "enterprise-client-slug"
python3 scripts/verify_enterprise_workspace.py \
  --workspace-id "<expected-workspace-id>" \
  --profile "enterprise-client-slug"
```

Fail closed on a missing/mismatched workspace, role, status, or billing mode. Re-run the identity preflight whenever switching clients.

## Source registration

Use the client's finalized Source Library asset; do not re-upload footage:

```bash
python3 scripts/list_assets.py --type video
python3 scripts/use_library_video.py --asset-id "<asset-id>"
python3 scripts/list_videos.py
```

`use_library_video.py` idempotently registers the asset as a processing `videoId`. Keep source asset ID and video ID distinct. Transcribe before AI suggestions or captioned work.

## Canonical editor snapshot

Create the clip, then initialize the exact current editor state with workspace, aspect, fit background, quality, caption enablement, and the complete approved caption style:

```bash
python3 scripts/initialize_editor_snapshot.py \
  --workspace-id "<expected-workspace-id>" \
  --profile "enterprise-client-slug" \
  --clip-id "<clip-id>" \
  --aspect-ratio 9:16 \
  --fit-background blur \
  --quality high \
  --captions \
  --caption-style-json @style.json
```

Retain `editorVersion`, `editorStateHash`, and `clipSettingsRevision`. If `set_caption_style.py` mutates the style, replace all three initialization values with the mutation's returned values and retain its full normalized `captionStyle` and `captionStyleHash`. Never reuse the initialization identity after a style mutation.

For deliberate no-caption work, initialize with `--no-captions` and omit all style fields.

## Exact render, export, and ready delivery

For captioned enterprise work, use the exact recipe rather than direct legacy rendering:

```bash
python3 scripts/run_enterprise_exact_delivery.py \
  --workspace-id "<expected-workspace-id>" \
  --profile "enterprise-client-slug" \
  --clip-id "<clip-id>" \
  --style-json @style.json \
  --expected-editor-version "<latest-version>" \
  --expected-editor-state-hash "<latest-hash>" \
  --expected-clip-settings-revision "<latest-revision>" \
  --max-credits "<approved-cap>" \
  --no-outro
```

The first call is a read-only plan. Verify:

- exact workspace, clip, source, and snapshot identity;
- normalized style and 64-character style hash;
- style hash equals the retained mutation hash when a mutation ran;
- explicit outro policy and expected final duration;
- internal estimated usage is within the approved cap;
- `clientCreditChargeClip` is zero under usage-only settlement;
- no capability, spend-limit, identity, or state blocker.

Only then rerun the same request with `--confirm`. Advance only the returned plan hash. If processing continues, reuse the original request plus receipt `resumeToken`, plan hash, caption-style hash, and expected final duration. Do not repeat completed stages or create a replacement render.

The final receipt must prove render/export/delivery IDs, exact caption hash, current snapshot version/hash, output fingerprint, outro policy, and probed artifact duration. `deliver_export.py` is only a recovery path for an already eligible exact export; it accepts no caller-authored title or note.

Direct captioned enterprise `render_clip.py` is blocked because a legacy style request can replace exact fields. A deliberate no-caption `--no-captions --no-auto-reframe` path remains available. If a requested style capability is unsupported, report one product-owned blocked state; never ask the client to repair or save the editor.

## Client selection and publishing

The operator may create a `ready` deliverable. Only the client can select it in the portal. The operator must not select, unselect, or publish a merely ready item.

```bash
python3 scripts/list_deliverables.py \
  --workspace-id "<expected-workspace-id>" \
  --profile "enterprise-client-slug" \
  --export-id "<exact-export-id>" \
  --status selected
```

Before publishing, refresh connected/granted accounts and pin one exact platform/account plus the exact current selected export. Preserve snapshot ID and output fingerprint. Never select by display name and never combine multiple enterprise destinations in one request.

## Exactness invalidation

Changing source bounds, aspect, framing, quality, caption enablement/style, timeline media, audio, or outro policy invalidates downstream assumptions. Re-read state, intentionally create a new canonical snapshot/identity when required, re-render/export, re-run QA, and create a new ready delivery. Never reuse an older exactness receipt for a changed artifact.
