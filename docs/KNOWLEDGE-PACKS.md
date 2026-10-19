# Knowledge packs for roles and jobs

The objective is for a worker to find the requirements, procedure and evidence needed for its current job, and identify what remains unknown. A large collection of pages alone does not meet that objective.

## Current implementation

The Crawlee plugin creates `tmf-knowledge-pack/v1` source collections as JSON and Markdown: topic, tags, bounded collection scope, documents, source URLs, retrieval times, hashes, unavailable sources and limitations. It supports saved passage and artifact reads. These packs are unreviewed source material, not approved operational guidance. They are not automatically indexed or assigned to Roles.

## Operational pack contract — proposed next layer

Keep the existing KB ingestion/approval controls. A reviewed operational pack should identify:

| Field | Purpose |
| --- | --- |
| Role and job | Who needs it and which task it supports |
| Required inputs | What must be known before starting |
| Procedure and examples | Steps, worked examples, templates and expected outputs |
| Decision rules | Conditions, exceptions, stop points and escalation owner |
| Requirements | Product capabilities, integration contracts and acceptance criteria |
| Evidence | Source snapshot/passage references supporting consequential claims |
| Scope | Jurisdiction, product/version, effective dates and exclusions when established |
| Ownership | Reviewer, approval state, version, review date and refresh trigger |
| Access | Instance and permitted Roles; client material remains in its own instance |
| Gaps | Missing, conflicting, stale and unavailable information |

Do not fill unknown fields with guesses. A reviewer approving a procedure is a separate event from a crawler retrieving a page. New source snapshots should create a reviewable update rather than silently replacing approved instructions.

## Useful first packs

| Pack | Questions the pack should answer |
| --- | --- |
| Shared operations | How do we handle client data, record decisions, verify work and escalate failures? |
| Sales and assessment | Which client problems fit the offer, what evidence is needed, and what disqualifies a lead? |
| Customer service | What can be answered, what needs human handoff, and what evidence is retained? |
| Office management | Which intake, scheduling, invoice and follow-up procedures apply? |
| Commerce and payments | What are the order/refund/reconciliation flows and integration failure cases? |
| Payroll and tax research | Which authoritative requirements apply to the specified jurisdiction/date, and who reviews them? |
| Builders | What must be implemented, integrated and demonstrated for a client deliverable to be accepted? |

Agents use relevant knowledge for their assigned work. Builders use requirements and acceptance evidence to build. These remain separate jobs.

## Acceptance proof

Test one realistic task per pack. Record the retrieved passages, answer or action, missing inputs, escalation and reviewer result. Measure supported-claim coverage, correct exception handling, stale-information detection and whether another worker can repeat the procedure. A pack is useful when it improves those outcomes; document count is only a collection metric.
