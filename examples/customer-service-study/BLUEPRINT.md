# TMF customer-service automation pilot

Research date: 2026-10-19. Proposed service design; no client or production deployment. See evidence-report.md for reviewed vendor facts, qualifications and source URLs. Requirements CS-001–CS-032 live in report.json and the generated workbook.

## What we can sell

Start with a paid support-systems assessment: map current intake, identity checks, knowledge, routing, actions, exceptions, volumes and support ownership. Deliver a ranked automation backlog and a scoped pilot proposal. Commercial demand and price still need direct buyer validation.

The first implementation offer is one inbound text channel connected to an existing support system, with a small client-approved set of intents. Candidate intents: general FAQs, authenticated order-status lookup and collecting missing information. The client chooses which are eligible. Include human takeover, recovery queue, dashboard, knowledge maintenance and a documented exit/export path. Quote implementation separately from ongoing operations and third-party usage.

Offer managed operations only with a named owner and agreed coverage: queue supervision, incident response, knowledge updates, sampled quality review, vendor-change monitoring, reconciliation and monthly outcome reporting. A recurring fee pays for this operating work; it is not simply a markup on model calls.

## Scope boundaries

Pilot includes: discovery, a single selected channel, identity and permission controls, durable case history, approved knowledge, limited read-only business tools, response approval policy, human escalation, operational controls and acceptance evidence.

Separately scoped expansion: voice/IVR, recordings and transcription, multilingual support, workforce scheduling, outbound campaigns, payment execution, refunds, payroll, medical or legal decisions and migration from an existing helpdesk. These require their own research and acceptance. No implied promise that this blueprint covers all enterprise support requirements.

## Build versus buy

Build the differentiated workspace, policy controls, knowledge workflow, case/task links, action ledger, recovery UI and evidence-backed reporting. Prefer existing channel transport, routing, identity and helpdesk APIs where they meet the client's needs. A mature helpdesk can remain the authoritative case system; do not silently create a competing master record. If replacing it is the objective, ticket lifecycle, search, imports, attachments, portal access, notifications, SLAs and exports become additional product work.

Do not rebuild telecom delivery or payment processing for the first pilot. Provider choice depends on access, costs, portability, security and channel needs; this study does not establish a vendor winner.

## Records builders need

| Record | Minimum fields and constraints |
|---|---|
| Tenant | ID, authoritative provider bindings, timezone, retention policy version; isolate every query and job |
| Customer identity | Customer ID, provider mappings, verification method/time/expiry; address alone is not account authority |
| Case | Local/provider ID, requester, channel, subject, lifecycle state, owner/queue, priority, current version, timestamps |
| Message | Provider ID, case ID, actor, visibility, content reference, received/sent time, delivery state, attachment metadata |
| Knowledge version | Article/version, owner, access scope, approved date, expiry, digest and source URL |
| Routing task | Case ID, provider task ID, workflow/queue, routing state, version, deadline; separate from case state |
| Reservation | Task ID, worker, offer ID, offer status, offered/accepted/expired times; retain history |
| Action intent | Case/version, operation ID, authority, tool, parameter digest, approval, idempotency key reference, state |
| Action outcome | Provider request/object ID, attempted/confirmed time, result classification, reconciliation evidence |
| Audit event | Tenant, actor, action, before/after version references, decision/policy version; redact sensitive content |
| Reconciliation checkpoint | Provider, cursor/window, last durable event, completed time, gaps and retry status |

## Case lifecycle proposal

These are our proposed internal states, not a claim about a vendor's exact status values. Map them explicitly to the chosen helpdesk.

| From | Trigger | To | Required consequence |
|---|---|---|---|
| received | Persisted valid intake | triage | Link identity, deduplicate and select owner policy |
| triage | Eligible grounded response | active | Record supporting knowledge and authorized action |
| triage / active | Uncertain answer, customer request or restricted action | queued_for_human | Freeze bot sends and persist context plus escalation reason |
| queued_for_human | Confirmed worker acceptance | human_active | Set owner atomically; retain queue/offer history |
| queued_for_human | Offer rejection, timeout or nobody available | queued_for_human | Requeue or create callback; alert responsible queue owner |
| active / human_active | Waiting on customer | waiting_customer | Set explicit SLA pause rule and follow-up date |
| active / human_active | Resolution evidence recorded | resolved | Record reason and confirmed response outcome |
| resolved | Eligible customer reply during agreed reopen window | triage | Preserve history and measure repeat contact |
| any nonterminal | Ambiguous action outcome or integration outage | recovery_required | Visible operator work item; no invented success |
| recovery_required | Authoritative readback and owner resolution | prior valid state | Record result and resume from durable checkpoint |

Routing completion does not automatically resolve the case. Bot confidence is not customer identity, action authority or proof of delivery.

## Integration contracts to implement

Adapters normalize provider intake into tenant/provider/event ID, received time, original payload reference and signature-validation result. Acknowledgment follows durable admission; slow work runs from the persisted event. Define which payloads can be retained and for how long.

Use provider APIs for case read/update and comment creation, with explicit visibility and optimistic concurrency where available. Store provider and internal versions. A conflict triggers readback and a new decision; avoid overwriting a newer human action.

The dispatch worker consumes a durable outbox containing one authorized intent. Record planned, dispatching, confirmed, failed or outcome_unknown. A network timeout is outcome_unknown until reconciled. An internal operation ID is useful even when a provider offers no idempotent-send guarantee; it cannot create a guarantee the provider lacks.

Handoff creates or links a routing task, tracks reservation attempts and confirms worker acceptance. Takeover increments the case's automation fence. Every pending automated send must recheck that fence before dispatch. If the provider cannot prevent a send already in flight, expose that race and define the mitigation with the client.

Reconciliation uses the selected provider's supported listing/export APIs. Pin cursor semantics, update windows, deletions, pagination, quotas and clock overlap in the adapter specification. These details remain discovery work, rather than assuming all APIs support the same change feed.

## Acceptance suite for the pilot

All cases below are planned acceptance scenarios, not executed support-system tests. Record fixtures, expected outcome, actual provider readback, audit entries and reviewer decision for each. CS requirement IDs give more precise pass conditions.

1. Approved general question returns a supported answer with the exact article version.
2. Unknown policy creates a useful human handoff and preserves the customer's question.
3. Wrong identity cannot retrieve an order or sensitive conversation.
4. Duplicate webhook does not duplicate a reply, task or business action.
5. Omitted webhook is recovered and produces one durable effect.
6. Concurrent human takeover stops queued automation and exposes any in-flight send uncertainty.
7. Rejected/expired offers requeue; unavailable humans leave a visible owned callback.
8. Expired knowledge and hostile text cannot authorize a new tool action.
9. Provider timeout, stale version and outage each enter the correct recoverable state.
10. Oversized body and external attachment URL do not truncate silently or leak credentials.
11. Kill switch stops new sends; recovery reconciles previous attempts before resuming.
12. Export and restore preserve case ownership, visibility, action outcomes and required audit references.

## Security and assurance discovery

A scoped client review must identify data classes, roles, access paths, retention, deletion, residency, subprocessors, incident duties, authentication requirements and any requested attestations. Assign an owner and evidence for each control. Vendor certifications do not certify our implementation. No legal, PCI, privacy, recording-consent or sector compliance conclusion is made here. Voice and financial actions remain separate until their applicable requirements are established.

Proposed baseline engineering includes isolation, role checks, encrypted transport/storage, managed secrets, safe attachment handling, signed webhook verification, audit logs, backups, restore drills and incident controls. Validate them in the actual deployment; this list is not an assurance report.

## Economics worksheet

Use measured client inputs, not invented ROI. Define eligible monthly cases V, average baseline handling minutes H, validated safe deflection fraction D, and loaded labor cost per hour L. Gross theoretical labor capacity is V × H × D ÷ 60 × L. This is potential capacity, not necessarily cash savings: staffing and workload determine realization.

Subtract incremental transport, model/retrieval, hosting/storage, software seats, integration maintenance, human review, escalation rework and support/on-call costs. Add one-time discovery, implementation, migration, training and acceptance costs to the payback model. Measure quality and repeat contacts alongside savings; a fast wrong answer is a cost.

Illustration only: 2,000 eligible cases × 8 minutes × 25% deflection ÷ 60 × $30/hour = $2,000/month of theoretical capacity. With $1,200/month incremental operation, the illustration leaves $800/month before implementation, overhead and tax. These inputs are fictional and are not a quote, forecast or benchmark.

Quote only after volumes, entitlements, provider pricing, risk, acceptance work and support coverage are known. Use a capped pilot budget, usage alerts and a clear stop condition.

## Delivery sequence

Discovery → signed scope and architecture → sandbox connector → policy/knowledge and case model → handoff/recovery → acceptance corpus → supervised pilot → measured client review → any expansion. Estimate each after access and dependencies are known. Client acceptance and observed outcomes decide readiness; generated documents do not.

## Research-tool verdict

This run produced a concrete scoping and acceptance pack from official documentation plus actual REA analysis. It exposed durable-case retention, handoff acceptance, comment visibility, concurrency and uncertain-action recovery that a feature checklist misses.

The main gap is upstream: the research was operator-assisted. The repository can validate/render a supplied report and import REA evidence, but it does not yet autonomously investigate, resolve source conflicts or audit its own conclusions. The first-party schema also cannot represent this entire blueprint structurally; this document is a companion until that model exists.

This is useful for a discovery workshop and build backlog. It is not yet an independently reviewed implementation estimate, a validated sales offer or a production-ready customer-service service.
