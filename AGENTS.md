# ClipIt Agent Pack

You are working with the ClipIt Agent Pack — skills and Python script bindings that let any agent operate [ClipIt](https://clipit.dev), a video clipping platform (import → transcribe → clip → caption → render → export → publish → analyze).

## Setup (do this once)

1. Confirm the environment variables are set (never echo the key):
   - `CLIPPER_API_KEY` — from ClipIt → Settings → API Keys → Connect an Agent
   - `CLIPPER_BASE_URL` — usually `https://clipit.dev`
2. Install script dependencies: `pip install -r requirements.txt`
3. Verify the account connection: `python scripts/list_videos.py` — any successful response (even an empty list) means you are connected. A `401` means the key is wrong; a `403` names a permission the user must enable on the key in ClipIt Settings.

If Node is available, the richer path is the ClipIt CLI: `npm install -g @clipit-ai/cli`, store the key with `clipit auth set-key --stdin`, then `clipit agent install <your-framework-name>` (any name works) and verify with `clipit videos list`.

### Enterprise workspace setup (ClipIt team only)

Enterprise keys are for the ClipIt team operating contracted client workspaces, not normal users. Store each admin-created workspace key in its own non-default ClipIt CLI profile; never put a workspace key in the shared `CLIPPER_API_KEY` environment variable. Activate that profile with `clipit auth use <profile>` (or select it explicitly with `CLIPIT_PROFILE`), then run `python scripts/verify_enterprise_workspace.py --workspace-id <expected-id>` before reading or changing client content. Continue only when it verifies the exact active workspace, `team_operator` role, and `enterprise_usage_only` billing. A successful `list_videos.py` call alone is not an enterprise identity check.

With a non-default profile selected, the Python client deliberately ignores ambient personal `CLIPPER_API_KEY` and `CLIPPER_BASE_URL` settings; a missing named-profile key fails closed. Keep one named profile per workspace and rerun the identity preflight whenever switching clients.

For an enterprise clip, use this exact authority-preserving sequence:

1. Activate the workspace's named profile and run `verify_enterprise_workspace.py --workspace-id <expected-id> --profile <profile>`.
2. Run `list_assets.py --type video`, select an asset, run `use_library_video.py --asset-id <asset-id>`, and confirm the resulting processing video with `list_videos.py`.
3. Run `transcribe_video.py --video-id <video-id> --wait` before captioned renders or AI clip suggestions. Manual clips without captions do not require transcription.
4. Create the clip with `create_clip.py`.
5. Run `initialize_editor_snapshot.py` with the exact workspace, clip, aspect ratio, fit background, quality, and explicit caption choice. Its safe default is `--no-captions --caption-style minimal`.
6. Run `render_clip.py` with the same aspect ratio, quality, and caption choice, plus `--workspace-id <expected-id> --profile <profile> --no-auto-reframe --wait`.
7. Run `start_export.py` with export framing that matches the snapshot, wait for completion, then run `deliver_export.py` to create a `ready` deliverable.
8. Leave selection to the client. The agent may confirm `selected` with `list_deliverables.py`, but it must never select or publish a merely `ready` deliverable.

Changing aspect ratio, quality, caption enablement/style, or framing after initialization makes the snapshot stale. Reinitialize intentionally instead of bypassing the export identity check.

## How to work

- Each capability is documented in `clipper/<skill>/SKILL.md` — read the relevant one before acting. Skills: video-management, clip-creation, export-rendering, thumbnail-generation, caption-generation, broll-generation, social-publishing, account-insights, machine-payments.
- Every script in `scripts/` is a thin REST binding with `--help`.
- **Cost preflight:** ordinary API keys spend the user's $CLIP credits on rendering, exports, B-Roll, thumbnails, and social posts. Check `python scripts/get_credits_balance.py` and `python scripts/estimate_cost.py` before paid operations, and confirm with the user before spending. Enterprise workspace keys record usage without debiting the client balance; social publishing still requires explicit approval.
- **Credit top-ups:** when credits are insufficient, read `clipper/machine-payments/SKILL.md`, discover live rails and products, and create a payable attempt only after explicit approval or a configured budget policy.
- Long-running jobs: poll renders with `scripts/wait_for_job.py`, exports with `scripts/wait_for_export.py` (exports use a different endpoint — do not mix them up).
- Live, permission-scoped operating instructions: `python scripts/get_agent_instructions.py --target generic --format markdown`.

## Boundaries

- Never write the API key into files, logs, chat, or prompts.
- Never operate on enterprise content until the named-profile identity preflight matches the expected workspace ID.
- Treat publishing to social platforms and credit-spending operations as user-approval checkpoints.
