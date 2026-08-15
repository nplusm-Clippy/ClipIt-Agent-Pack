# ClipIt Agent Pack

You are working with the ClipIt Agent Pack — skills and Python script bindings that let any agent operate [ClipIt](https://clipit.dev), a video clipping platform (import → transcribe → clip → caption → render → export → publish → analyze).

## Setup (do this once)

1. Confirm the environment variables are set (never echo the key):
   - `CLIPPER_API_KEY` — from ClipIt → Settings → API Keys → Connect an Agent
   - `CLIPPER_BASE_URL` — usually `https://clipit.dev`
2. Install script dependencies: `pip install -r requirements.txt`
3. Verify the account connection: `python scripts/list_videos.py` — any successful response (even an empty list) means you are connected. A `401` means the key is wrong; a `403` names a permission the user must enable on the key in ClipIt Settings.

If Node is available, the richer path is the ClipIt CLI: `npm install -g @clipit-ai/cli`, store the key with `clipit auth set-key --stdin`, then `clipit agent install <your-framework-name>` (any name works) and verify with `clipit videos list`.

## How to work

- Each capability is documented in `clipper/<skill>/SKILL.md` — read the relevant one before acting. Skills: video-management, clip-creation, export-rendering, thumbnail-generation, caption-generation, broll-generation, social-publishing, account-insights, machine-payments.
- Every script in `scripts/` is a thin REST binding with `--help`.
- **Cost preflight:** ordinary API keys spend the user's $CLIP credits on rendering, exports, B-Roll, thumbnails, and social posts. Check `python scripts/get_credits_balance.py` and `python scripts/estimate_cost.py` before paid operations, and confirm with the user before spending. Enterprise workspace keys record usage without debiting the client balance; social publishing still requires explicit approval.
- **Credit top-ups:** when credits are insufficient, read `clipper/machine-payments/SKILL.md`, discover live rails and products, and create a payable attempt only after explicit approval or a configured budget policy.
- Long-running jobs: poll renders with `scripts/wait_for_job.py`, exports with `scripts/wait_for_export.py` (exports use a different endpoint — do not mix them up).
- Live, permission-scoped operating instructions: `python scripts/get_agent_instructions.py --target generic --format markdown`.

## Boundaries

- Never write the API key into files, logs, chat, or prompts.
- Treat publishing to social platforms and credit-spending operations as user-approval checkpoints.
