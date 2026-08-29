---
name: clipper-machine-payments
description: Discover current ClipIt payment capabilities and prepare an explicitly approved credit top-up through a live supported rail. Use only when the user asks to buy credits or a paid operation is blocked and the user authorizes a product, amount, rail, and budget.
license: MIT
metadata:
  version: "2.0.0"
  tags: [ClipIt, Billing, x402, Stripe, Link, MPP, Credits]
  hermes:
    tags: [ClipIt, Billing, x402, Stripe, Link, MPP, Credits]
    requires_toolsets: [terminal]
---

# ClipIt Machine Payments

Use with `clipit-operator`. Discover the live catalog and ready rails for the active profile; never infer availability, price, or signing fields from this document. The Python scripts below are the supported fallback bindings.

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

Requesting the MPP `paymentUrl` without `Authorization: Payment` returns a challenge. A Link-authenticated Stripe payer can authorize and retry it with a Shared Payment Token while also sending `X-Api-Key`.

Use Stripe Link CLI to sign in and select a saved Link payment method. Probe the payment URL, pass its complete `WWW-Authenticate` value to `mpp decode`, and use the decoded Stripe `network_id` and exact amount when creating the spend request. Before requesting approval, require decoded `request_json.amount` and `request_json.currency` to match the catalog `amountCents` and currency exactly; abort on any mismatch. The human must approve that request before payment. Stripe SPT requests identify the merchant with `network_id`, so do not pass `--merchant-name` or `--merchant-url`.

```bash
link-cli auth login
link-cli payment-methods list
link-cli mpp decode --challenge '<complete WWW-Authenticate header>'

link-cli spend-request create \
  --credential-type shared_payment_token \
  --network-id <decoded-stripe-network-id> \
  --payment-method-id <link-payment-method-id> \
  --amount <catalog-amount-cents> \
  --currency usd \
  --context "Purchase the exact ClipIt credit product and amount that the user approved through the Stripe Link machine-payment rail for this ClipIt account." \
  --line-item "name:<catalog-product-label>,unit_amount:<catalog-amount-cents>,quantity:1" \
  --total "type:total,display_text:Total,amount:<catalog-amount-cents>" \
  --request-approval

link-cli mpp pay "<paymentUrl>" \
  --spend-request-id <approved-link-spend-request-id> \
  --method POST \
  --header "X-Api-Key: $CLIPPER_API_KEY"

link-cli report create \
  --domain clipit.dev \
  --outcome success \
  --spend-request-id <approved-link-spend-request-id> \
  --step "ClipIt MPP payment returned HTTP 200 and the receipt was fulfilled"
```

Report every completed purchase attempt. Use `success` only after ClipIt returns a fulfilled receipt; otherwise report `blocked` or `abandoned` with a short non-secret failure step.

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
