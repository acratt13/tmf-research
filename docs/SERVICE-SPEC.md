# TMF professional services specification

Version 0.1 · 2026-10-19 · Proposed delivery standard, not a claim of service readiness.

## 1. Purpose and scope

Define what must be researched, built, tested, priced and supported before offering TMF software and automation services. Each engagement selects a bounded subset of this specification. This document is a master checklist; product, jurisdiction, provider and client-specific specifications remain required. A checkbox or generated report is not operational proof or certification.

Service families are grounded in recurring buyer requests for process assessments, connected business software, customer support, revenue operations, document processing, ecommerce, managed workspaces and outsourced implementation. Historical requests demonstrate examples to investigate; they do not establish current contracts, achievable margins, market size or delivery capability.

## 2. Service catalog

| ID | Offer and buyer outcome | Required deliverables | Acceptance and recurring care |
| --- | --- | --- | --- |
| S01 | Business systems / automation assessment: identify worthwhile changes | Current workflow map; application/data inventory; observed failures; baseline volumes and costs; ranked opportunities; risk/dependency register; phased scope | Client validates the map and priorities; findings trace to evidence. Optional periodic reassessment |
| S02 | Custom premium software / SaaS: deliver a usable business application | Discovery, domain rules, UX, architecture, tenancy model, implemented scope, migration, deployment, training and operating manual | Critical journeys and durable results verified in the target environment; maintenance and release ownership assigned |
| S03 | Workflow automation and integrations: remove specific manual steps | Trigger/action contracts; mappings; identity/permission model; retries; deduplication; exception queues; reconciliation | Normal, duplicate, failed and unknown outcomes exercised; monitor and repair integrations as upstream systems change |
| S04 | Customer service / contact center: route and resolve customer requests | Channel inventory; queues; case lifecycle; identity checks; approved knowledge; booking/CRM actions; escalation; human takeover; quality evaluation | Cross-channel case continuity, correct routing, failed-tool behavior and human handoff demonstrated; ongoing content/quality review |
| S05 | Payments / billing / revenue operations: connect sales to cash | Quote/contract/invoice lifecycle; provider integration; payment allocation; credits; refunds; disputes; reconciliation; accounting ownership | Partial/overpayments and failed/duplicate notifications handled; money movement verified separately from API submission |
| S06 | Ecommerce operations: connect ordering and fulfillment | Catalog/variants; inventory ownership; carts; checkout provider; orders; tax/shipping dependencies; returns/refunds; customer support; reporting | Inventory concurrency, duplicate checkout events, partial fulfillment and return scenarios pass; reconciliation and store care |
| S07 | Office manager / executive operations: organize work across systems | Mail/calendar/document/task routing; deadlines; vendors; bills; approvals; delegated access; escalation; activity history | Timezone/deadline behavior, context preservation and authority limits demonstrated; access and workflow reviews |
| S08 | HR / payroll / tax operations: move approved records through a controlled process | Legal-employer mapping; worker/time inputs; effective-dated compensation; locked pay-run snapshot; preview/approval; provider handoff; filing/payment evidence; correction workflow | Sample and parallel runs reconciled with responsible payroll/accounting owner; no release inferred from submission. Jurisdiction/provider-specific scope required |
| S09 | Documents / knowledge / intake: make records usable | Ingestion; OCR/extraction; provenance; confidence; human correction; access controls; document versions; grounded retrieval; exports | Extracted values trace to source locations; permission filtering and low-confidence review tested; ongoing content stewardship |
| S10 | Analytics / reporting: provide defensible operational visibility | Metric dictionary; source ownership; mappings; quality checks; dashboards; drill-through; refresh/failure states | Sample totals reconcile with approved source records; stale/failed data remains visible; ongoing metric/change review |
| S11 | Managed client workspace: operate an isolated working environment | Client-owned identities/data boundaries; approved tools; role configuration; knowledge/workflow setup; backups; monitoring; handoff/exit | Isolation and restore tested in target deployment; support windows, responsibilities, budgets and escalation agreed |
| S12 | Agency / white-label delivery: provide repeatable fulfillment | Partner/client boundary; per-client scope and isolation; reusable modules; release/acceptance packs; incident routing; support agreement | Each deployment accepted independently; maintenance and client communications ownership explicit |
| S13 | Technical security / automation-readiness assessment: identify control gaps | Defined scope; asset/data flows; authorization; evidence-backed findings; severity rationale; prioritized remediation; retest report | Findings reproducible within authorized scope. Formal assurance work is separately scoped with the appropriate assessor |
| S14 | Deep research / software breakdown: turn questions into reusable decisions | Investigation plan; source register; documented/observed distinctions; REA artifacts where applicable; contradictions; requirements; diagrams; report exports | Claim/source review, limits and unresolved questions visible; refreshed when material sources or rules change |

S08 is a priority research track. It is not a promise to implement a universal tax engine or perform every payroll/tax service. Similarly, S04 must distinguish software-assisted service from staffing a contact center, and S11 must distinguish workspace administration from unlimited managed IT.

## 3. Every service needs an offer card

Record the target buyer, problem, disqualifiers, included outcomes, excluded work, prerequisites, delivery method, acceptance evidence, commercial terms, operating costs, expected client effort, recurring responsibilities and exit arrangement. Name the responsible owner and backup. State which steps require a domain professional, provider agreement or additional authority.

Offers progress through: researched → defined → demonstrated → pilot-delivered → supported → repeatable. No service is marked demonstrated or pilot-delivered solely because this specification exists. Initial readiness across this catalog is **not established**; attach actual evidence per offer.

## 4. Discovery and engagement contract

Before quoting implementation, establish business entities, jurisdiction, locations, users, roles, volumes, peaks, system of record per object, current process and exceptions, baseline performance, integrations, API entitlements, available test environments, data classes, retention, budget and deadline constraints.

Create a signed statement of work with deliverables, acceptance scenarios, client dependencies, ownership/IP terms, third-party and usage charges, change control, payment milestones, support boundaries and exit deliverables. Use reviewed commercial/legal templates for the actual market; this file is not a contract. Confirm the named client authority for external actions and account administration.

Discovery is itself a bounded paid deliverable where useful. Assessment recommendations must distinguish measured facts from interview estimates and proposed savings. Do not sell a speculative time-saving figure as demonstrated ROI.

## 5. Reusable workflow contract

For every workflow, specify:

- Stable ID/version; business owner; purpose; users; in-scope entities and records.
- Trigger; schedule/timezone; prerequisites; validated inputs and source identities.
- Normal sequence; state definitions; legal transitions; outputs and durable readback.
- Action authority; approval scope; approval expiry; escalation and human takeover.
- Duplicate protection; ordering; concurrency; timeout; cancellation; retry rules.
- Partial completion; external effect unknown; reconciliation; reversal/compensation.
- Error visibility; exception owner; recovery instructions; audit events.
- Data classification; retention/deletion; credential references; integration budgets.
- Executable acceptance cases and required evidence; deployment/rollback ownership.

A transport timeout after submission must not automatically produce another money movement, message, invoice or filing. Retrying requires an operation-specific duplicate/reconciliation strategy. A resumed job is not proof an external effect did or did not happen.

## 6. Product and engineering requirements

**P01 — Identity and isolation.** Explicit user, organization and client boundaries. Authentication, session lifecycle, server-enforced resource/action permissions, privileged access control, account recovery, offboarding and service identities. Test cross-client and cross-role denial, including searches, attachments and exports.

**P02 — Data ownership.** Define authoritative system and conflict policy per entity. Preserve external IDs/version fields, history, provenance and attachment ownership. Validate imports, map identifiers, detect duplicates, reconcile counts/totals, rehearse migration and retain rollback evidence. Client operational data remains in the client's designated data environment; the provider's personal workspace is not its default store.

**P03 — Integration reliability.** Document API version, scopes, consent, expiration, rate limits, pagination, webhooks, signature validation, retries, idempotency where supported, reconciliation and deprecation handling. Sandbox access is not production permission. Record partial/failed reads without displaying fabricated zeroes.

**P04 — Premium user experience.** Agreed information architecture and task flows; readable hierarchy; keyboard operation; responsive layouts; loading/empty/error/offline states; clear destructive-action consequences; accessible forms; discoverable recovery. Validate rendered task completion with representative users, not screenshots alone.

**P05 — Operations.** Separate development/test/production; deployment identity; migrations; release and rollback; monitoring; alert routing; incident handling; backup and tested restore; agreed recovery objectives; capacity/cost budgets; upstream dependency inventory. A backup file existing is not a successful restore.

**P06 — AI behavior.** Assign bounded tools, data and roles. Treat retrieved material as untrusted evidence, not instructions. Deterministic code owns money, tax and official scoring rules where those are in scope. Evaluate retrieval, unsupported assertions, refusal/escalation, conflicting sources, data leakage and tool failures. AI recommendations and approved external actions remain distinct.

**P07 — Evidence and audit.** Record actor, client, action, source/version, permission/approval reference, time, correlation, outcome and error/reconciliation state. Protect logs from unauthorized mutation and access. Redact secrets and sensitive payloads according to policy; do not copy complete confidential documents into logs by default.

**P08 — Ownership and exit.** Define accounts, domains, repositories, licenses, credentials and data ownership. Deliver usable exports, source where contracted, configuration, manuals and known limitations. Test the agreed handoff; account cancellation must not silently make client data unrecoverable.

## 7. Domain depth that must not disappear in a generic checklist

**Customer service/contact center:** hours/holidays; routing and escalation; case ownership; identity verification before account changes; recording/transcript handling; channel consent/opt-out; abusive or urgent conversations; language; knowledge freshness; staff takeover; channel/provider failure. Confirm communications and privacy obligations for actual locations and channels before activation.

**Ecommerce/payments:** distinguish authorization, capture, settlement, refund, reversal and dispute states as supported by the selected provider. Preserve original invoice/order totals, partial payments, unapplied funds, credits and bank reconciliation. Define inventory reservation/overselling, shipping/tax providers, subscription changes, failed fulfillment and refund allocation. Currency precision and rounding require a selected explicit policy.

**Office operations:** inbox and calendar authority, who can send versus draft, conflicting bookings, daylight-saving changes, confidential messages, document signatures, vendor changes, approval amounts, missed deadlines and absent approvers. A scheduling assistant's access must not imply access to all compensation or financial records.

**Payroll/taxes:** employer/work-location jurisdictions, worker classification owner, pay schedules, time and overtime rules, effective dates, retroactive changes, deductions/benefits, garnishments where applicable, leave, final pay, off-cycle/correction runs, payment failures, filing/deposit confirmations, year-end records and reconciliation. Maintain a jurisdiction/date/source register. A named payroll/tax professional or authorized provider validates the actual domain scope. Federal, state/local and non-US coverage cannot be inferred from one provider integration.

The IRS distinguishes third-party payroll arrangements and notes employer liability depends on the arrangement and circumstances. The contract must explicitly allocate tasks and retain payment/filing evidence; outsourcing alone does not establish that the employer's obligations disappeared. [IRS guidance](https://www.irs.gov/businesses/small-businesses-self-employed/outsourcing-payroll-and-third-party-payers)

## 8. Security, assurance and obligations register

No universal set of certificates applies to every TMF service. Maintain one applicability record per client/deployment: requirement, source/version, jurisdiction or contractual trigger, system boundary, accountable party, control/evidence, assessor where needed, review date, status and unresolved gap.

| Track | Meaning and required scoping |
| --- | --- |
| SOC reporting | SOC 2 is an examination/report concerning selected trust-services controls and a described system. Decide whether the customer's procurement needs an actual report and what boundary it covers; a supplier report does not attest to our entire service. [AICPA SOC resources](https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services) |
| ISO/IEC 27001 | Requirements for an information security management system; certification is distinct from implementing individual technical controls. Evaluate business need, organizational scope and independent certification route. [ISO](https://www.iso.org/standard/27001) |
| Card payments | Define merchant/service-provider responsibilities, card-data flow and applicable PCI DSS validation with the relevant parties. PCI SSC warns unofficial compliance certificates are not the recognized validation documents. [PCI SSC](https://blog.pcisecuritystandards.org/beware-of-pci-dss-compliance-certificates) |
| Privacy/communications/employment/sector obligations | Jurisdiction, data, role and activity-specific research required. Assign a qualified review owner and record applicable contractual/provider requirements; do not claim blanket legal coverage |
| Accessibility | Define the target standard and assessment scope. Basic automated/preliminary checks cannot establish comprehensive conformance. [W3C evaluation guidance](https://www.w3.org/WAI/test-evaluate/preliminary/) |
| Operational security | Threat model, access/secrets management, encryption/key custody, patching, secure development, vendor review, detection, incident response and restore evidence; scope and verify each control |

An internal readiness assessment is not an independent certification or regulated financial audit. Marketing claims must match actual evidence, organization, system and review period.

## 9. Required delivery pack and acceptance

Every project supplies: approved discovery brief and scope; requirements/traceability matrix; workflow/data/integration diagrams; architecture and permission design; applicability register; source/configuration ownership; migration report; test/evidence pack; deployment/rollback and restore instructions; user/admin training; support runbook; known limitations; cost/usage baseline; handoff/exit pack.

Trace each requirement through design, implementation, scenario, target environment, actual result, evidence location and acceptance owner. Test happy paths plus denial, duplicate, concurrency, partial completion, unknown effect and recovery. Client acceptance is separately recorded; passing internal tests does not replace it.

For PDFs, Markdown, diagrams and editable office/design exports, retain the report revision and evidence references. Export success includes opening the artifact and checking essential content. An editor connector is ready only after open → edit → save → reopen → export/import has been verified for that adapter.

## 10. Pricing, margins and ongoing service

Choose fixed-scope assessment, paid discovery, milestone implementation, recurring care or bounded usage pricing per offer. Estimate actual delivery/review effort, provider/API/model usage, hosting/storage, licenses, migration, specialist review, support workload and contingency. Record assumptions; use agent execution estimates where appropriate rather than presenting automatic human-week estimates.

Model gross contribution as revenue less direct delivery, infrastructure, provider, specialist and support costs. Separate hypothetical benefits from client-confirmed outcomes. Set usage caps, overage rules, change requests and renewal terms. Avoid unlimited-support promises before staffing and incident coverage are established.

## 11. Readiness evidence and open work

The current associated research includes documentation studies and bounded REA inspections. That establishes research inputs, not production readiness across this catalog. This public repository begins with an evidence/report core; autonomous research roles and editor integrations remain to be built and verified.

To activate any offer: select a narrow buyer/problem → complete the missing domain/provider research → define the offer and scope → demonstrate the critical paths → run a bounded client pilot → verify operating/support costs → obtain acceptance → then claim repeatable delivery. Maintain separate statuses for researched, implemented, tested, client-accepted, released and supported.

Still required per engagement: current provider entitlements, exact region/rules, commercial/legal review, production identity/architecture, domain specialist availability, real performance/reliability/restore evidence, and actual client acceptance. No service in this master specification is declared universally certified, compliant or ready for sale.
