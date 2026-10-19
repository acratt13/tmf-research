# Customer-service automation: a buildable pilot blueprint

What must TMF scope, build and verify to offer a premium customer-service automation pilot?

## Summary

Proposed offer: assess the current support workflow, then pilot one inbound text channel and a small approved intent set with reliable human takeover. Own the durable case, permissions, recovery and operating evidence. Reuse channel/routing infrastructure; expand voice and financial actions only after separate scoping. Research pack is useful for discovery and build planning; service implementation and commercial demand remain unproven.

Evidence labels describe the input. Validation checks structure and references; it does not verify the truth of a claim.

## Findings

\[DOCUMENTED\] Public replies and private notes share the comment model. New comments are submitted through ticket create/update, not a comment-create endpoint. Displayed author and authenticated updater can differ. (ZD-COMMENTS)

\[DOCUMENTED\] Comment bodies above 64 kB can be truncated without an error. Attachment URLs can lead outside the vendor host; credentials must not follow them to third parties. (ZD-COMMENTS)

\[DOCUMENTED\] Webhook delivery can duplicate or omit events. The documented invocation log covers seven days. An integration needs durable reconciliation beyond that window. (ZD-WEBHOOKS)

Limit: Reconciliation is our proposed response to the documented delivery limits.

\[DOCUMENTED\] A routing Task is not the durable customer case: rejected or timed-out reservations can return a task to pending; terminal task records are deleted after five minutes. (TW-LIFECYCLE)

\[DOCUMENTED\] Task updates support ETag/If-Match checks and return 412 on version mismatch. Updating attributes and moving a task to wrapping/completed requires separate requests. (TW-TASK)

\[DOCUMENTED\] Reservations are offers to a worker. A reservation that receives no handling decision within its workflow timeout leaves the task available for other workers. (TW-RESERVATION)

\[DOCUMENTED\] Twilio recommends SDK request-signature validation, accounting for the exact webhook URL and all received parameters rather than a frozen field list. (TW-SECURITY)

\[DOCUMENTED\] Stripe API v1 retains the first executed response for a key, including 500 responses; keys may be pruned after at least 24 hours. Reusing a pruned key can create a new operation. (STRIPE-IDEMPOTENCY)

\[OBSERVED\] Selected SDK modules serialize task assignmentStatus, reservation reservationStatus and If-Match headers; task and reservation are distinct resource wrappers. (REA-TWILIO)

Limit: REA parsed selected inert release files; direct source readback confirmed these fields. This does not validate the remote API or complete SDK.

\[PROPOSED\] A sellable first offer is an assessment plus a narrow assisted-service pilot, followed by separately scoped managed operations. Demand and willingness to pay remain untested. (no external evidence)

## Proposed requirements and acceptance

CS-001: Validate provider webhook signatures before admitting work

Acceptance: Tampered body, wrong URL and invalid signature each create no case or action; valid vendor fixtures pass.

CS-002: Persist and deduplicate incoming events by tenant, provider and external event identity

Acceptance: Replaying one event 20 times yields one case effect; same identifier in another tenant stays independent.

CS-003: Keep a durable case independent of temporary routing resources

Acceptance: Expired/deleted task still leaves full case history, owner and unresolved customer request visible.

CS-004: Verify customer identity before revealing account-specific information

Acceptance: Unverified sender gets generic help; mismatched account cannot retrieve another customer order.

CS-005: Enforce tenant and record permissions across retrieval, tools and exports

Acceptance: Adversarial cross-tenant identifiers and disallowed knowledge return denial without data exposure.

CS-006: Set public/private visibility explicitly on every comment action

Acceptance: Internal-note content never appears in customer reply, retrieval context for that customer or exported transcript.

CS-007: Preserve actor, displayed author and authenticated updater separately

Acceptance: Audit readback distinguishes the service account from the employee shown as author.

CS-008: Check reply size and attachment destination before sending

Acceptance: Oversized body is held for editing; external attachment fetch sends no vendor credentials and obeys size/type limits.

CS-009: Use approved versioned knowledge with owner, access scope and expiry

Acceptance: Expired or inaccessible article is excluded; an answer records the article version supporting it.

CS-010: Escalate unsupported answers and hostile instructions in customer content

Acceptance: A request to ignore policy cannot expand tool authority; absent evidence yields a handoff rather than invented policy.

CS-011: Model queue, routing task and reservation as separate linked records

Acceptance: Rejected reservation remains in history and a new offer links to the same unresolved case.

CS-012: Confirm acceptance before treating a human handoff as complete

Acceptance: Timeout/no available worker leaves a named queue owner and fallback callback task; customer sees an accurate pending state.

CS-013: Fence automated replies as soon as human takeover is committed

Acceptance: Concurrent queued bot send and takeover permit no bot send after the takeover version commits.

CS-014: Re-read and resolve version conflicts before changing task state

Acceptance: Stale If-Match gets 412; newer owner/state survives and operator receives the conflict.

CS-015: Configure skills, capacity, business hours, overflow and abandonment rules

Acceptance: After-hours, full-capacity and abandoned-request scenarios preserve a recoverable case and correct destination.

CS-016: Persist outbound intent and use an idempotent dispatch boundary

Acceptance: Crash before send, during send and after acknowledgment is recovered without claiming unconfirmed delivery.

CS-017: Represent ambiguous provider outcomes explicitly and reconcile them

Acceptance: A send timeout records outcome unknown; readback or human resolution establishes its result before retry.

CS-018: Keep money-moving actions outside the first pilot; design their approval contract

Acceptance: Refund request captures order, amount, currency and responsible owner, but cannot execute a refund in pilot.

CS-019: Scope future payment idempotency to provider API version and operation identity

Acceptance: For an approved future refund, changed parameters cannot reuse a key; pruned-key and repeated-500 recovery uses authoritative lookup.

CS-020: Reconcile missed events using provider-supported read APIs and checkpoints

Acceptance: A deliberately omitted webhook is recovered from a known fixture; checkpoint advances only after durable application.

CS-021: Bound retries, record dead letters and provide an operator recovery queue

Acceptance: Persistent provider failure ends in visible manual recovery with attempt history, without silently dropping the case.

CS-022: Treat multi-request task completion as a recoverable workflow

Acceptance: Failure between attribute update and completion does not mark the case resolved; recovery reads both outcomes.

CS-023: Use managed secret references, least privilege and rotation

Acceptance: Revoked integration credential stops actions visibly; replacement succeeds without credentials in receipts or exports.

CS-024: Record append-only action history with retention and redacted logs

Acceptance: Case owner can reconstruct each action and decision; retention deletion removes scoped content with an auditable receipt.

CS-025: Define SLA clocks, pause reasons, timezone and escalation owner

Acceptance: Weekend, daylight-saving and waiting-on-customer fixtures match the signed service schedule.

CS-026: Measure successful resolution separately from bot response or handoff

Acceptance: Dashboard reports eligible cases, repeat contacts, acceptance failures, confirmed delivery and correction rate with clear denominators.

CS-027: Provide kill switch, export, restore and vendor outage runbook

Acceptance: Operator disables automated sends, restores a fixture backup and resumes only after reconciliation.

CS-028: Gate pilot on evaluated cases and actual sandbox workflows

Acceptance: Signed pilot corpus includes happy path, ambiguity, wrong identity, stale policy, duplicate, omission, timeout, race and unavailable human; no unexplained high-risk failures.

CS-029: Sign scope, authoritative systems, dependencies and support ownership

Acceptance: Client approves included intents/channels, integration access, exceptions, data handling and exit deliverables before go-live.

CS-030: Establish baseline volumes and a costed pilot budget

Acceptance: Client inputs measured eligible volume, handling time, provider usage and QA/support effort; budget states uncertainty and stop threshold.

CS-031: Scope voice, recording, telecom and jurisdiction obligations separately

Acceptance: Before voice launch, responsible owner records applicable consent, recording, number/channel provisioning and specialist decisions for each served location.

CS-032: Assess assurance and sector obligations against actual customer requirements

Acceptance: Procurement/data classification review identifies requested attestations, contractual controls and any specialist signoff; no certification is inferred from vendor selection.

## Unknowns and remaining work

No customer interview, current buying intent or willingness-to-pay validation; this is a researched service blueprint, not market proof.

Client identity, jurisdiction, channel mix, monthly volume, peak load, languages and accessibility requirements remain unspecified.

Authoritative case system, account identity proof, approved knowledge corpus and allowed automatic intents require client selection.

Vendor plan entitlements, scopes, rate limits, export coverage and current pricing have not been verified in an authenticated tenant.

No sandbox email/chat/voice delivery, real handoff, refund, intrusion assessment, disaster recovery or production customer-service flow was run.

Privacy, retention, recording, sector obligations and requested assurance need a scoped client review; this report establishes no legal or certification conclusion.

Research was performed by an operator using web tools and the real REA repo. The project CLI validated/rendered evidence; it did not autonomously find or assess sources.

No independent second reviewer checked every claim. Source availability and structural validation do not establish semantic support.

General-purpose deep-research orchestration, browser acquisition, source snapshots, semantic review and integrated Craft adapters remain unimplemented in the core tool.

## Evidence register

ZD-COMMENTS — Zendesk Ticket Comments \[available\]; retrieved 2026-10-19T06:56:49.685031+00:00

url: https://developer.zendesk.com/api-reference/ticketing/tickets/ticket\_comments/

scope: Comment visibility, creation API, author/updater identity, size limits and attachment trust

limitations: Selected official documentation reviewed; no authenticated vendor tenant or end-to-end integration exercised.

ZD-WEBHOOKS — Zendesk webhook delivery \[available\]; retrieved 2026-10-19T06:56:49.685031+00:00

url: https://developer.zendesk.com/documentation/webhooks/creating-and-monitoring-webhooks/

scope: Duplicate/missing delivery, invocation monitoring and bounded retries

limitations: Selected official documentation reviewed; no authenticated vendor tenant or end-to-end integration exercised.

TW-TASK — Twilio Task resource \[available\]; retrieved 2026-10-19T06:56:49.685031+00:00

url: https://www.twilio.com/docs/taskrouter/api/task

scope: Task attributes, conditional updates and lifecycle operations

limitations: Selected official documentation reviewed; no authenticated vendor tenant or end-to-end integration exercised.

TW-LIFECYCLE — Twilio task lifecycle \[available\]; retrieved 2026-10-19T06:56:49.685031+00:00

url: https://www.twilio.com/docs/taskrouter/lifecycle-task-state

scope: Routing states, assignment rejection and task record lifetime

limitations: Selected official documentation reviewed; no authenticated vendor tenant or end-to-end integration exercised.

TW-RESERVATION — Twilio reservation resource \[available\]; retrieved 2026-10-19T06:56:49.685031+00:00

url: https://www.twilio.com/docs/taskrouter/api/reservations

scope: Offer acceptance, rejection and reservation timeout

limitations: Selected official documentation reviewed; no authenticated vendor tenant or end-to-end integration exercised.

TW-SECURITY — Twilio secure webhooks \[available\]; retrieved 2026-10-19T06:56:49.685031+00:00

url: https://www.twilio.com/docs/usage/webhooks/webhooks-security

scope: SDK signature validation with exact URL and evolving parameters

limitations: Selected official documentation reviewed; no authenticated vendor tenant or end-to-end integration exercised.

STRIPE-IDEMPOTENCY — Stripe idempotent requests \[available\]; retrieved 2026-10-19T06:56:49.685031+00:00

url: https://docs.stripe.com/api/idempotent\_requests

scope: API v1 repeated responses, bounded key retention and parameter consistency

limitations: Selected official documentation reviewed; no authenticated vendor tenant or end-to-end integration exercised.

REA-TWILIO — REA static inspection of Twilio Node SDK 6.2.0 \[partial\]; retrieved 2026-10-19T06:56:49.685031+00:00

url: https://registry.npmjs.org/twilio/-/twilio-6.2.0.tgz

artifact\_sha256: 214905aa27dc460e872affb5b871957f33d4dca3b2400fe5460778b7252fa6a2

evidence\_id: ev\_1739f6b032ef6690663855d14c4ab9f5ec559d1fb07f14382a9a51420185a7b2

scope: Two selected task/reservation JS modules; 37 graph nodes and 44 relationships. Exact release archive integrity matched registry metadata.

limitations: Selected-file static analysis; dependencies absent, no server behavior or legal state-transition proof. Original envelope retained locally; published review is a derived summary.
