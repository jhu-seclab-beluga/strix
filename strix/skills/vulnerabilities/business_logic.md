---
name: business-logic
description: Business logic testing for workflow bypass, state manipulation, and domain invariant violations
---

# Business Logic Flaws

Business logic flaws exploit intended functionality to violate domain invariants: move money without paying, exceed limits, retain privileges, or bypass reviews. They require a model of the business, not just payloads.

## Attack Surface

- Financial logic: pricing, discounts, payments, refunds, credits, chargebacks
- Account lifecycle: signup, upgrade/downgrade, trial, suspension, deletion
- Authorization-by-logic: feature gates, role transitions, approval workflows
- Quotas/limits: rate/usage limits, inventory, entitlements, seat licensing
- Multi-tenant isolation: cross-organization data or action bleed
- Event-driven flows: jobs, webhooks, sagas, compensations, idempotency

## High-Value Targets

- Pricing/cart: price locks, quote to order, tax/shipping computation
- Discount engines: stacking, mutual exclusivity, scope (cart vs item), once-per-user enforcement
- Payments: auth/capture/void/refund sequences, partials, split tenders, chargebacks, idempotency keys
- Credits/gift cards/vouchers: issuance, redemption, reversal, expiry, transferability
- Subscriptions: proration, upgrade/downgrade, trial extension, seat counts, meter reporting
- Refunds/returns/RMAs: multi-item partials, restocking fees, return window edges
- Admin/staff operations: impersonation, manual adjustments, credit/refund issuance, account flags
- Quotas/limits: daily/monthly usage, inventory reservations, feature usage counters

## Reconnaissance

### Workflow Mapping

- Derive endpoints from the UI and proxy/network logs; map hidden/undocumented API calls, especially finalize/confirm endpoints
- Identify tokens/flags: stepToken, paymentIntentId, orderStatus, reviewState, approvalId; test reuse across users/sessions
- Document invariants: conservation of value (ledger balance), uniqueness (idempotency), monotonicity (non-decreasing counters), exclusivity (one active subscription)

### Input Surface

- Hidden fields and client-computed totals; server must recompute on trusted sources
- Alternate encodings and shapes: arrays instead of scalars, objects with unexpected keys, null/empty/0/negative, scientific notation
- Business selectors: currency, locale, timezone, tax region; vary to trigger rounding and ruleset changes

### State and Time Axes

- Replays: resubmit stale finalize/confirm requests
- Out-of-order: call finalize before verify; refund before capture; cancel after ship
- Time windows: end-of-day/month cutovers, daylight saving, grace periods, trial expiry edges

## Key Vulnerabilities

### State Machine Abuse

- Skip or reorder steps via direct API calls; verify server enforces preconditions on each transition
- Replay prior steps with altered parameters (e.g., swap price after approval but before capture)
- Split a single constrained action into many sub-actions under the threshold (limit slicing)

### Concurrency and Idempotency

- Parallelize identical operations to bypass atomic checks (create, apply, redeem, transfer)
- Abuse idempotency: key scoped to path but not principal → reuse other users' keys; or idempotency stored only in cache
- Message reprocessing: queue workers re-run tasks on retry without idempotent guards; cause duplicate fulfillment/refund

### Numeric and Currency

- Floating point vs decimal rounding; rounding/truncation favoring attacker at boundaries
- Cross-currency arbitrage: buy in currency A, refund in B at stale rates; tax rounding per-item vs per-order
- Negative amounts, zero-price, free shipping thresholds, minimum/maximum guardrails

### Quotas, Limits, and Inventory

- Off-by-one and time-bound resets (UTC vs local); pre-warm at T-1s and post-fire at T+1s
- Reservation/hold leaks: reserve multiple, complete one, release not enforced; backorder logic inconsistencies
- Distributed counters without strong consistency enabling double-consumption

### Refunds and Chargebacks

- Double-refund: refund via UI and support tool; refund partials summing above captured amount
- Refund after benefits consumed (downloaded digital goods, shipped items) due to missing post-consumption checks

### Feature Gates and Roles

- Feature flags enforced client-side or at edge but not in core services; toggle names guessed or fallback to default-enabled
- Role transitions leaving stale capabilities (retain premium after downgrade; retain admin endpoints after demotion)

## Advanced Techniques

### Event-Driven Sagas

- Saga/compensation gaps: trigger compensation without original success; or execute success twice without compensation
- Outbox/Inbox patterns missing idempotency → duplicate downstream side effects
- Cron/backfill jobs operating outside request-time authorization; mutate state broadly

### Microservices Boundaries

- Cross-service assumption mismatch: one service validates total, another trusts line items; alter between calls
- Header trust: internal services trusting X-Role or X-User-Id from untrusted edges
- Partial failure windows: two-phase actions where phase 1 commits without phase 2, leaving exploitable intermediate state

### Multi-Tenant Isolation

- Tenant-scoped counters and credits updated without tenant key in the where-clause; leak across orgs
- Admin aggregate views allowing actions that impact other tenants due to missing per-tenant enforcement

## Bypass Techniques

- Content-type switching (JSON/form/multipart) to hit different code paths
- Method alternation (GET performing state change; overrides via X-HTTP-Method-Override)
- Client recomputation: totals, taxes, discounts computed on client and accepted by server
- Cache/gateway differentials: stale decisions from CDN/APIM that are not identity-aware

## Special Contexts

### E-commerce

- Stack incompatible discounts via parallel apply; remove qualifying item after discount applied; retain free shipping after cart changes
- Modify shipping tier post-quote; abuse returns to keep product and refund

### Banking/Fintech

- Split transfers to bypass per-transaction threshold; schedule vs instant path inconsistencies
- Exploit grace periods on holds/authorizations to withdraw again before settlement

### SaaS/B2B

- Seat licensing: race seat assignment to exceed purchased seats; stale license checks in background tasks
- Usage metering: report late or duplicate usage to avoid billing or to over-consume

## Chaining Attacks

- Business logic + race: duplicate benefits before state updates
- Business logic + IDOR: operate on others' resources once a workflow leak reveals IDs
- Business logic + CSRF: force a victim to complete a sensitive step sequence

## Testing Methodology

1. **Enumerate state machine** - Per critical workflow (states, transitions, pre/post-conditions); note invariants
2. **Build Actor × Action × Resource matrix** - Unauth, basic user, premium, staff/admin; identify actions per role
3. **Test transitions** - Step skipping, repetition, reordering, late mutation
4. **Introduce variance** - Time, concurrency, channel (mobile/web/API/GraphQL), content-types
5. **Validate persistence boundaries** - All services, queues, and jobs re-enforce invariants

## Validation

1. Show an invariant violation (e.g., two refunds for one charge, negative inventory, exceeding quotas)
2. Provide side-by-side evidence for intended vs abused flows with the same principal
3. Demonstrate durability: the undesired state persists and is observable in authoritative sources (ledger, emails, admin views)
4. Quantify impact per action and at scale (unit loss × feasible repetitions)

## False Positives

- Promotional behavior explicitly allowed by policy (documented free trials, goodwill credits)
- Visual-only inconsistencies with no durable or exploitable state change
- Admin-only operations with proper audit and approvals

## Impact

- Direct financial loss (fraud, arbitrage, over-refunds, unpaid consumption)
- Regulatory/contractual violations (billing accuracy, consumer protection)
- Denial of inventory/services to legitimate users through resource exhaustion
- Privilege retention or unauthorized access to premium features

## Pro Tips

1. Start from invariants and ledgers, not UI—prove conservation of value breaks
2. Test with time and concurrency; many bugs only appear under pressure
3. Recompute totals server-side; never accept client math—flag when you observe otherwise
4. Treat idempotency and retries as first-class: verify key scope and persistence
5. Probe background workers and webhooks separately; they often skip auth and rule checks
6. Validate role/feature gates at the service that mutates state, not only at the edge
7. Explore end-of-period edges (month-end, trial end, DST) for rounding and window issues
8. Use minimal, auditable PoCs that demonstrate durable state change and exact loss
9. Chain with authorization tests (IDOR/Function-level access) to magnify impact
10. When in doubt, map the state machine; gaps appear where transitions lack server-side guards

## Summary

Business logic security is the enforcement of domain invariants under adversarial sequencing, timing, and inputs. If any step trusts the client or prior steps, expect abuse.

## BELUGA E-Commerce Checkout Definition

```toml
# E-Commerce Checkout Model Definition
# Complete data-channel definition: metadata, constants, variables, and
# invariants. The handwritten counterpart of the code-channel definition
# (domains/_ecommerce/_dsl_model.py); an equivalence test pins the two.

[metadata]
name = "E-Commerce Checkout"
description = "Invariant model for e-commerce checkout flows"
author = "beluga"

# ── Constants ────────────────────────────────────────────────────────

[constants]
# Comparison slack absorbing two-decimal currency rounding.
float_tolerance = 0.01
# Sanity cap on one line's ordered units; beyond it is an out-of-range defect.
max_quantity = 9999
# Lowest sane total/items ratio: discounts may shrink the total to 10%.
min_total_ratio = 0.1
# Highest sane total/items ratio: shipping and tax may inflate up to 10x.
max_total_ratio = 10.0

# ── Variables ────────────────────────────────────────────────────────

[[variables]]
name = "price"
var_type = "FLOAT"
data_source = "DATABASE"
optional = false
pair_group = "line_item"
description = """
Unit selling price of a single product, retrieved from the database \
and used in cart/checkout total calculations. The per-item price, not \
a line subtotal or an order total. Look for variables like $price, \
$p_price, $product_price, $unit_price, or $current_price that hold \
one product's price read from a database query result. Do not match \
the line subtotal (price times quantity), the order total, shipping, \
or a discounted price."""

[[variables]]
name = "quantity"
var_type = "INT"
data_source = "USER_INPUT"
optional = false
pair_group = "line_item"
description = """
Number of units of a product the customer ordered for each cart or \
order line. Bind the count the application stores, charges, or uses \
in the line calculation after any validation and normalization. \
A request value is eligible when the application uses it unchanged, \
even if validation is absent or the count violates an invariant. \
Observe an inline normalization at its result. Look for variables \
like $qty, $quantity, $cart_qty, or $item_quantity where they supply \
the cart/order quantity. A quantity-bearing name or lack of a later \
assignment does not establish this role. Do not match a product, item, \
or cart identifier ($_GET['id'], $_GET['itemsid'], product_id) — that \
selects which product, not how many — nor product stock, coupon \
redemption counts, any monetary amount, or a number_format() display \
copy."""

[[variables]]
name = "total"
var_type = "FLOAT"
data_source = "UNSURE"
optional = false
description = """
Final order total the customer is charged at checkout, equal to \
subtotal plus shipping and tax minus discounts. The amount owed \
before payment, not the amount actually paid. Look for variables like \
$final_total, $order_total, $grand_total, $total_amount, or \
$total_price computed server-side on the checkout page. Do not match \
the pre-adjustment subtotal, a single product price, or the money \
received after payment (that is `amount_paid`)."""

[[variables]]
name = "discount"
var_type = "FLOAT"
data_source = "UNSURE"
optional = true
description = """
Monetary amount the application deducts from the order subtotal once a \
coupon or promotional offer is applied. A deduction in currency the \
system records on the order, not a redemption count or a usage limit. \
Look for variables like $discount, $discount_amount, $coupon_discount, \
$discount_total, $reduction, or $promo_discount. Do not match coupon \
usage counters (`coupon_used_count`), coupon caps \
(`coupon_usage_limit`), tax, or shipping."""

[[variables]]
name = "shipping"
var_type = "FLOAT"
data_source = "UNSURE"
optional = true
description = """
Delivery fee added to the order total, determined by shipping method, \
weight, or destination. The cost of delivering the order, not the \
goods themselves or the tax on them. Look for variables like \
$shipping, $shipping_cost, $shipping_fee, $delivery_fee, $freight, or \
$express_fee. Do not match the product price, the order subtotal, \
tax, or the order total."""

[[variables]]
name = "tax"
var_type = "FLOAT"
data_source = "UNSURE"
optional = true
description = """
Tax amount charged on the order, such as sales tax or VAT. The tax \
component in currency, not the shipping fee or the discount. Look for \
variables like $tax, $tax_amount, $tax_total, $vat, $tax_value, or \
$tax_rate_amount. Do not match a tax rate or percentage, the shipping \
fee, the discount, or the order total."""

[[variables]]
name = "subtotal"
var_type = "FLOAT"
data_source = "UNSURE"
optional = true
description = """
Sum of line items (price times quantity across all cart items) before \
shipping, tax, and discounts are applied. The pre-adjustment cart \
amount, not the final charged total. Look for variables like \
$subtotal, $sub_total, $cart_total, $items_total, or $line_total. Do \
not match the order total (which includes shipping, tax, and \
discounts), a single product price, or the amount paid."""

[[variables]]
name = "stock"
var_type = "INT"
data_source = "DATABASE"
optional = true
description = """
Available inventory count for a product, read from the database \
during add-to-cart or checkout validation. The units on hand, not the \
units the customer ordered. Look for variables like $stock, \
$qty_in_stock, $inventory, $available_qty, $product_stock, or \
$stock_quantity fetched from a products/inventory table before \
allowing the order to proceed. Do not match the ordered quantity \
(`quantity`), coupon counts, or any monetary amount."""

[[variables]]
name = "checkout_currency"
var_type = "STRING"
data_source = "DATABASE"
optional = true
description = """
Currency code in effect while the cart/checkout page displays prices \
and computes totals, read before payment begins. The display-side \
currency, not the one sent to the payment gateway. Look for variables \
like $currency, $currency_code, or $cur read from the database or \
session during cart rendering or total calculation. Do not match the \
currency used in the payment handler or order-insertion logic (that \
is `payment_currency`)."""

[[variables]]
name = "payment_currency"
var_type = "STRING"
data_source = "DATABASE"
optional = true
description = """
Currency code in effect when payment is processed or the order is \
created, as the application stores it in the payment handler or \
order-insertion logic. The payment-side currency, not the one shown on \
the cart page. Look for variables like $currency, $payment_currency, \
$cur, or $money_code resolved during payment or order creation. Do not \
match the currency used while rendering the cart or computing totals \
(that is `checkout_currency`)."""

[[variables]]
name = "amount_paid"
var_type = "FLOAT"
data_source = "DATABASE"
optional = true
description = """
The money actually received for the order, reported by the payment \
gateway callback/notify handler and persisted on the paid order or \
payment record. Distinct from `total`: this is what the customer \
paid, not what the order is supposed to cost. Look for variables like \
$paid_amount, $pay_price, $total_fee, $amount_received, $captured, or \
$paid_price, populated only after payment succeeds. Do not match the \
pre-payment order total, the cart total, or a refund amount."""

[[variables]]
name = "wallet_before"
var_type = "FLOAT"
data_source = "DATABASE"
optional = true
description = """
The customer's prepaid account balance — wallet, store credit, or \
loyalty points — read before it is spent on an order, taken from the \
user/account record at the start of the payment or wallet-apply step. \
A cross-order asset held on the account, not a property of one order. \
The balance prior to the debit, not after. Look for variables like \
$wallet, $balance, $user_money, $store_credit, $ballance, or $points \
read before the deduction. Do not match the order total or the amount \
still due on the order (that is `total`), the amount being spent, \
the post-spend balance, or a refund amount."""

[[variables]]
name = "wallet_after"
var_type = "FLOAT"
data_source = "DATABASE"
optional = true
description = """
The customer's prepaid account balance — wallet, store credit, or \
loyalty points — persisted after it is spent on an order, written \
back to the user/account record once the wallet debit is applied. The \
balance following the debit, not before. Look for the same variables \
as `wallet_before` ($wallet, $balance, $user_money, $store_credit) at \
the point they are saved after subtraction. Do not match the \
pre-spend balance (`wallet_before`), the order total, the amount paid \
by card, or the amount still due on the order."""

[[variables]]
name = "coupon_usage_limit"
var_type = "INT"
data_source = "DATABASE"
optional = true
description = """
The fixed maximum redemptions allowed for a coupon/voucher/promo \
code, read from the coupon definition record. The cap (denominator), \
not how many times it has been used. Look for variables like \
$usage_limit, $use_limit, $max_use, $max_uses, $total_count, or \
$per_user_limit that bound permitted redemptions. Pair with \
`coupon_used_count`. Do not match product stock, cart item quantity, \
pagination limits, or rate-limit settings."""

[[variables]]
name = "coupon_used_count"
var_type = "INT"
data_source = "DATABASE"
optional = true
description = """
How many times a coupon/voucher/promo code has already been redeemed, \
incremented when an order applying it is placed. The running tally \
(numerator) compared against `coupon_usage_limit`, never the cap \
itself. Look for variables like $used, $used_count, $use_count, \
$times_used, or $redeemed read from the coupon or coupon-usage record. \
Do not match the usage cap, product stock, cart quantity, or total \
order count."""

[[variables]]
name = "order_status"
var_type = "STRING"
data_source = "DATABASE"
optional = true
description = """
The payment-state label persisted on the order record when checkout \
completes or the payment callback confirms, holding values such as \
'paid', 'pending', or 'unpaid'. Look for variables like $status, \
$order_status, $payment_status, or $pay_status written to the orders \
table, as in $order->update(['status' => 'paid']). Do not match a \
shipping or fulfilment status, an HTTP status code, a boolean paid \
flag, or the money received (that is `amount_paid`)."""

# ── Invariants ────────────────────────────────────────────────────────────
# Expression text uses the invariant expression syntax
# (docs/modeling/model-definition.md). price and quantity are observed
# once per cart line (pair group "line_item"), so
# PairedSum(price, quantity) is the order's line-item total. Derived
# scalars judge the settled (last) value via Single, not every
# transient a mid-checkout probe captures.

[[invariants]]
name = "price_positive"
description = "Product price must be positive"
expression = "All(price, It > 0)"

[[invariants]]
name = "quantity_positive"
description = "Quantity must be a positive integer"
expression = "All(quantity, It > 0)"

# Out-of-range category only: q <= 0 is quantity_positive's class, so
# the two invariants flag disjoint defect classes.
[[invariants]]
name = "quantity_bounded"
description = "Quantity must be within [1, max_quantity]"
expression = "All(quantity, Implies(It > 0, And(It >= 1, It <= max_quantity)))"

[[invariants]]
name = "total_positive"
description = "Order total must be positive"
expression = "Single(total) > 0"

[[invariants]]
name = "discount_non_negative"
description = "Discount must not be negative"
expression = "All(discount, It >= 0)"

[[invariants]]
name = "discount_bounded"
description = "Discount must not exceed the subtotal"
expression = "And(Single(discount) >= 0, Implies(PairedSum(price, quantity) > 0, Single(discount) <= PairedSum(price, quantity) + float_tolerance))"

[[invariants]]
name = "shipping_non_negative"
description = "Shipping cost must not be negative"
expression = "All(shipping, It >= 0)"

[[invariants]]
name = "tax_non_negative"
description = "Tax amount must not be negative"
expression = "All(tax, It >= 0)"

[[invariants]]
name = "subtotal_positive"
description = "Subtotal must be positive"
expression = "Single(subtotal) > 0"

[[invariants]]
name = "stock_non_negative"
description = "Stock must not be negative"
expression = "All(stock, It >= 0)"

[[invariants]]
name = "stock_sufficient"
description = "Stock must be >= ordered quantity (no overselling)"
expression = "Single(stock) >= Single(quantity)"

[[invariants]]
name = "currency_consistent"
description = "Currency must match between checkout and payment"
expression = "Single(checkout_currency) == Single(payment_currency)"

[[invariants]]
name = "total_gte_subtotal"
description = "Order total >= price * quantity (prevents underpricing)"
expression = "Single(total) >= PairedSum(price, quantity) - float_tolerance"

[[invariants]]
name = "total_consistent"
description = "Total ratio to subtotal between min_total_ratio and max_total_ratio"
expression = "Implies(PairedSum(price, quantity) > 0, And(Single(total) > 0, Single(total) / PairedSum(price, quantity) >= min_total_ratio, Single(total) / PairedSum(price, quantity) <= max_total_ratio))"

[[invariants]]
name = "subtotal_matches_items"
description = "Subtotal equals sum of price * quantity within tolerance"
expression = "Abs(Single(subtotal) - PairedSum(price, quantity)) <= float_tolerance"

[[invariants]]
name = "payment_covers_total"
description = "Amount paid must be at least the order total (no underpayment)"
expression = "Single(amount_paid) >= Single(total) - float_tolerance"

[[invariants]]
name = "coupon_within_usage_limit"
description = "Coupon used count must not exceed its usage limit"
expression = "Single(coupon_used_count) <= Single(coupon_usage_limit)"

[[invariants]]
name = "wallet_conserved"
description = "Wallet balance never increases when spent on an order"
expression = "Single(wallet_after) <= Single(wallet_before) + float_tolerance"

[[invariants]]
name = "paid_order_has_payment"
description = "An order marked paid must have a positive total and a payment record"
expression = "Implies(Single(order_status) == 'paid', And(Single(total) > 0, Present(amount_paid)))"
```
