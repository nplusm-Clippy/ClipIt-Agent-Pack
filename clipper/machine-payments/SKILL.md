---
name: clipper-machine-payments
description: Discover and prepare ClipIt credit top-ups through direct x402, Stripe-managed x402, or Stripe Link MPP
version: 1.0.0
author: nplusm-Clippy
license: MIT
platforms: [macos, linux, windows]
metadata:
  tags: [ClipIt, Billing, x402, Stripe, Link, MPP, Credits]
  hermes:
    tags: [ClipIt, Billing, x402, Stripe, Link, MPP, Credits]
    requires_toolsets: [terminal]
required_environment_variables:
  - name: CLIPPER_API_KEY
    prompt: "Enter your ClipIt API key"
    help: "Get one at https://clipit.dev -> Settings -> API Keys -> Connect an Agent"
    required_for: "Owned payment attempts and receipts"
---

# ClipIt Machine Payments

## When to Use

Use this skill when a paid ClipIt operation is blocked by insufficient credits or the user asks an agent to buy a prepaid period or top-up. Subscription-period purchases and top-ups both add credits, and credits stack.

## Safety Gate

- Default autopay is off.
- Do not create a payable attempt unless the human approved the catalog product, price, rail, and budget, or the user already configured an explicit budgeted autopay policy.
- Use only product keys and amounts returned by the live catalog.
- Use a stable idempotency key for retries.
- Never print or store API keys, wallet private keys, Link credentials, Shared Payment Tokens, or signed payment payloads.
- Continue paid work only after the receipt shows fulfillment or the credit balance is sufficient.

## Rails

| Provider | Payment source | Settlement destination | Payment protocol |
|----------|----------------|------------------------|------------------|
| `x402_direct` | Base USDC wallet | ClipIt Base treasury wallet | x402 `PAYMENT-SIGNATURE` |
| `stripe_x402` | Base USDC wallet | ClipIt Stripe balance through a unique deposit address | x402 `PAYMENT-SIGNATURE` |
| `stripe_mpp` | Stripe Link/Card Shared Payment Token | ClipIt Stripe balance | MPP `Authorization: Payment` |

Select only a rail whose catalog entry reports `enabled: true` and `ready: true`. `configured` means credentials exist; `verified` means a live rail has completed its required end-to-end proof.

## Procedure

1. Check balance with `python scripts/get_credits_balance.py`.
2. Discover live rail status with `python scripts/get_payment_capabilities.py`.
3. Read server-controlled products with `python scripts/get_billing_catalog.py`.
4. Obtain approval, then create an attempt with `--confirm` and a stable idempotency key.
5. Give the returned `paymentUrl` to a compatible payer.
6. Poll the attempt and fetch its receipt.
7. Recheck the credit balance before starting paid ClipIt work.

```bash
python scripts/create_payment_attempt.py \
  --product-key boost \
  --provider stripe_mpp \
  --idempotency-key agent-run-001 \
  --confirm

python scripts/get_payment_attempt.py --attempt-id <attemptId>
python scripts/get_payment_receipt.py --attempt-id <attemptId>
python scripts/get_credits_balance.py
```

## Paying the Challenge

### Stripe Link/Card MPP

Requesting the MPP `paymentUrl` without `Authorization: Payment` returns a challenge. A Link-authenticated Stripe payer can authorize and retry it with a Shared Payment Token while also sending `X-Api-Key`. For example, in an environment where Stripe Link CLI is installed and the user has approved its spend:

```bash
link mpp pay "<paymentUrl>" --header "X-Api-Key: $CLIPPER_API_KEY"
```

### Direct or Stripe-Managed x402

Requesting either x402 `paymentUrl` without `PAYMENT-SIGNATURE` returns the exact network, USDC amount, destination, and timeout. Pass that challenge to an x402 v2 EVM payer configured with the user's approved Base wallet, then retry the same URL with `PAYMENT-SIGNATURE` and `X-Api-Key`.

The Agent Pack intentionally does not accept or persist a wallet private key. Wallet custody belongs in the user's signer or agent wallet runtime.

## Verification

- Attempt: `python scripts/get_payment_attempt.py --attempt-id <attemptId>`
- Receipt: `python scripts/get_payment_receipt.py --attempt-id <attemptId>`
- Effective prepaid access: `python scripts/get_billing_subscription.py`
- Credits: `python scripts/get_credits_balance.py`

A payment is complete only when the receipt has a fulfilled attempt and deposit or prepaid-period record. A protocol transaction by itself is not sufficient evidence of ClipIt credit fulfillment.

## Failure Handling

- `ready: false`: do not use that rail; choose another ready rail or ask the user.
- HTTP 409: the attempt expired or does not match the requested product; create a new approved attempt.
- HTTP 429: too many unpaid attempts; reuse an existing attempt or wait for expiry.
- Paid but no fulfillment: do not pay again. Poll the same attempt and receipt; Stripe webhooks and reconciliation can recover fulfillment idempotently.
