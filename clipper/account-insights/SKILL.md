---
name: clipper-account-insights
description: Inspect current ClipIt credit state, preflight paid work against a live estimate and spend cap, and review account, clip, post, or platform analytics. Use before metered operations or when the user asks about performance, affordability, usage, or top content.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Credits, Analytics, Cost Estimate, Reporting, Social Media]
  hermes:
    tags: [ClipIt, Credits, Analytics, Cost Estimate, Reporting, Social Media]
    requires_toolsets: [terminal]
---

# ClipIt Account Insights

Use with `clipit-operator`. Prefer current `clipit credits` and `clipit analytics` commands or discovered MCP tools; the Python scripts below are compatible REST fallbacks. Never quote a remembered price: run the live preflight for the exact operation and metrics.

## When to Use

Use this skill when the user wants to:
- Check their $CLIP credit balance
- Estimate the credit cost before paid operations
- Review aggregate social analytics
- Find top-performing clips or posts
- Inspect metrics for a specific social post

Estimate before expensive paid work: render/export, B-Roll generation, thumbnail generation, transcription, AI clip suggestions, and multi-platform social posting. Costs are reported in $CLIP.

## Quick Reference

| Operation | Preferred path | REST fallback |
|-----------|----------------|---------------|
| Check credits/usage | `clipit credits balance|usage --json` | `get_credits_balance.py` |
| Preflight cost/cap | `clipit credits estimate ... --json` or paid command `--max-credits` | `estimate_cost.py ... --max-credits <n>` |
| Analytics overview/top clips/post | `clipit analytics ... --json` | matching analytics scripts |

## Procedure

### Checking Credits

**When to use:** For ordinary personal keys when the user asks about account balance. Enterprise usage-only workspace keys intentionally cannot read owner balance/history; use the cost preflight below instead.

**Steps:**
1. Run `python scripts/get_credits_balance.py`
2. Read `balanceClip`, `lifetimeDepositedClip`, and `lifetimeConsumedClip`
3. If balance is low, pause before starting paid work

**Example:**
```bash
python scripts/get_credits_balance.py
```

### Estimating Cost

**When to use:** Before render/export/B-Roll/thumbnail/social/transcription work when enough metrics are known.

**Steps:**
1. Choose the operation, provider, optional model, and numeric metrics
2. Run `estimate_cost.py` with metrics as `key=value` pairs and the approved `--max-credits` cap when one exists
3. Continue only if `affordable` and `withinApprovalCap` are true and no spend-limit violation is returned
4. Report `internalEstimatedUsageClip` separately from `clientCreditChargeClip`; enterprise usage-only work must show a zero client charge

**Examples:**
```bash
python scripts/estimate_cost.py \
  --operation-type transcription \
  --provider deepgram \
  --model-id nova-3 \
  videoSeconds=120

python scripts/estimate_cost.py \
  --profile <workspace-profile> \
  --operation-type lambda_render \
  --provider aws_lambda \
  --model-id remotion-4.0 \
  --max-credits "<approved-cap>" \
  videoSeconds=45
```

### Reviewing Analytics

**When to use:** The user asks how their published content is performing.

**Steps:**
1. Run `python scripts/get_analytics_overview.py --days 30`
2. For platform breakdowns, add `--by-platform`
3. For top performers, run `python scripts/get_top_clips.py --metric views --limit 10`
4. For a specific post, run `python scripts/get_post_metrics.py --post-id <id>`

## Pitfalls

- **Separate usage from charge.** `internalEstimatedUsageClip` is operational usage, while `clientCreditChargeClip` is the client debit. Enterprise usage-only work reports the former and charges zero.
- **Do not request enterprise balance.** Workspace keys intentionally lack `credits_read`; `/api/v1/credits/preflight` evaluates cost and caps without disclosing balance/history.
- **Estimates require the right metrics.** For render/export, use `videoSeconds`. Provider/model names must match what the metering service expects.
- **Analytics depends on published posts.** Empty analytics can simply mean no connected social metrics have been captured yet.
- **Spend limits can block an affordable balance.** If `spendLimitViolation` is present, do not start the paid operation with the same API key.

## Verification

- **Balance checked:** Response includes `balanceClip` and `units: "clip"`
- **Preflight succeeded:** Response includes `internalEstimatedUsageClip`, `clientCreditChargeClip`, `settlementMode`, `affordable`, and `withinApprovalCap`, with no balance field
- **Analytics loaded:** Overview contains totals such as `totalViews` or platform rows
- **Top clips loaded:** Response is an array of clips/posts with a selected metric value
