# TMF Research: current capabilities and delivery roadmap

Status checked 2026-10-20. This is the public product roadmap; live project ownership,
decisions and work tracking remain in MC Canon. Future items below are plans, not
released features or delivery-date promises.

## Product direction

A useful standalone research tool that produces real, editable deliverables. It
also introduces people to TMF Systems and demonstrates the research, integration
and custom software work TMF can do. The standalone product should earn trust on
its own. MC adds connected context, agents, workflows and shared document work.

One engine, multiple job types and entry points. Spreadsheet is a delivery format,
not the name or limit of the prospect-intelligence product.

## What exists today

| Capability | Current boundary |
| --- | --- |
| Local browser workspace and CLI | Developer setup from GitHub; Python 3.11+ and authenticated Codex CLI 0.160.1 for research. No ordinary desktop installer yet. |
| Selectable research modes | Understand, Compare, Build, Audit and Offer a service can be combined. Quick, Detailed and Deep have bounded source, round and role-call budgets. |
| Research orchestration | Lead planning, source scouting, concurrent specialist calls, advisory Council perspectives, evidence review and bounded follow-up. Roles currently use the same provider. |
| Public source collection | Search leads become evidence after readable pages are fetched. Original bytes, extracted text, timestamps, URLs, hashes and unavailable-source states are retained. Not unrestricted authenticated platform access. |
| Actual REA integration | Configured local static software inspections retain the real REA envelope. Static findings do not establish runtime behavior. |
| Selected local document evidence | Operator-configured UTF-8 documents through CLI briefs; bounded size, optional expected hash and retained evidence. No general PDF/DOCX upload UI yet. |
| Reviewed, traceable research | Findings cite evidence; uncertain/unsupported claims can be held back. Coverage, caveats and gaps stay visible. Model review can still be wrong. |
| Saved research reader | Accepted analysis, findings, proposed requirements, matrices, source register, advisory disagreement and downloads. |
| Actual downloadable files | Markdown, HTML and builder JSON; PDF, DOCX, XLSX, PPTX and editable workflow diagram with configured optional engines. Exports are generated files, not MC canvas editing. |
| Research revisions and re-exports | Refine finished retained evidence into a separate reviewed revision, or select other export formats without repeating acquisition. Integrity checks preserve originals. |
| Run status and cancellation | Local history, progress, partial/failed/cancelled/interrupted states, bounded subprocesses and retained evidence. One workbench job at a time; no automatic crash resume. |
| Separate Crawlee worker | A deployed collection plugin supports bounded public collection, passage readback and JSON/Markdown source packs. Its shared research-engine acquisition path and complete MC actor workflow are not finished. |
| Public repository | Source, examples, installation instructions and documented limitations. No claim of customer-ready packaging or superior benchmark performance. |

### Evidence already produced

The DSH ecosystem research run produced 15 published reviewed findings, ten proposed
requirements and three matrices from 22 source records, using 21 bounded role calls
and an actual REA inspection. All requested formats were generated. Independent
readback checked a 27-page PDF, DOCX text, a 152-row worksheet, an 11-slide deck,
the workflow image and source/artifact hashes. The run remained partial where
coverage was incomplete. This proves that run and those files, not every future
topic, native Office interoperability or installed-MC integration.

## Already started, still unfinished

- Perplexity decision-trial adapter and fixtures exist. Live comparison is blocked
  on authorized credential access; no provider-quality result is established.
- Crawlee collection exists separately; make it a shared acquisition backend for
  research, prospecting and knowledge jobs.
- Document converters exist; purpose-specific document structures and consistent
  polished templates need work.
- MC has separate plugin/canvas work in progress. Coordinate with its owners;
  this roadmap does not create another canvas or plugin manager.

## Budget-first model setup

Andy, 2026-10-20: the immediate setup must be inexpensive. Keep the richer
research/multi-model Council arrangement documented as the recommended upgrade
configuration, subject to evaluation, rather than make it the default cost.

| Profile | Proposed setup | Status |
| --- | --- | --- |
| Current development | Existing authenticated Codex CLI; no extra provider account needed for that path. Subscription/usage limits still apply. | Implemented baseline, not cost-free inference. |
| Budget default | Evaluate an inexpensive tool-capable model such as DeepSeek V4.1 Flash; app owns retrieval, evidence retention and the Council workflow. Reuse evidence, select only relevant specialists, bound output and calls, and avoid automatic premium escalation. | Planned API adapter, quality/cost evaluation and cost controls; not wired or benchmarked. This is not a purpose-trained research model. |
| Recommended upgrade configuration | Research-focused backend, knowledge-backed dynamic specialists, separate critical review; optional Perplexity Agent API research presets and OpenRouter Fusion multi-model comparison. | Candidate configuration pending quality/cost tests; optional rather than required. |

Tongyi DeepResearch remains a purpose-trained research candidate, but its presence
on a model information page is not proof of a callable provider: the OpenRouter
public models catalog checked on 2026-10-20 did not include its ID. Confirm hosting
and the trained prompt/tool contract before a trial. Do not download weights or
provision self-hosting as an assumed budget shortcut.

Preserve evidence checks in every profile. Routing/triage models can reduce wasted
work; they do not replace the substantive researcher or source-support reviewer.
Record actual token/tool usage before quoting a per-job price. No provider switch,
paid trial, billing change or automatic premium fallback is made by this roadmap.

## What we will add

| Product area | Planned additions | Definition of done |
| --- | --- | --- |
| Real document products | Job-aware reports, company briefs, audits, proposals, comparison tables, prospect datasets and presentations; audience and format selection. Preserve editable source and evidence links. | A user completes a job, downloads its appropriate actual file, edits it in a supported editor and reopens the saved result. Content is purpose-built rather than one report dumped into different containers. |
| Prospect intelligence | Discover businesses or accept domains; retain identity, public business email/phone/contact routes, source and checked date; deduplicate; find service-relevant opportunities; export XLSX/CSV/JSON and company briefs. | A real sample can be audited row by row: contacts are source-backed, missing fields are honest, duplicates are handled and recommendations explain their basis. Published contact presence and email deliverability are separate checks. |
| Explainable qualification | Offer-specific fit, opportunity, buying signals, contact quality, research confidence and an overall outreach priority. Preserve disqualifiers, missing data, score version and reasons. | Each score can be traced to evidence and recomputed. Missing evidence is not invented. A heuristic priority is never presented as a calibrated chance of purchase. Conversion probabilities require actual outcome data and validation. |
| Demand discovery | Find explicit requests and described problems on the public web and through supported access to LinkedIn, Upwork, Fiverr and X. Preserve original request, date, budget/timeline when stated and available response route. | Demonstrate a permitted search/read path for each supported source and correctly distinguish buyer requests, complaints, job listings and seller offers. No promise of unrestricted scraping or hidden buyer requests. |
| RAG-ready knowledge packs | Human-readable document plus machine-readable chunks with stable IDs, parent/section references, source provenance, version, scope/access metadata, approval state and refresh information. Add ingestion/export adapters. | A representative retrieval test returns the right passage and citation, respects scope, identifies stale/superseded material and exposes missing knowledge. A collection or JSONL file alone is not proof of successful indexing. |
| Decision models | Evaluate Jev-style specialist decision models and Perplexity on the same labeled tasks; route job type, depth, roles, evidence follow-up and output selection. | Compare error rates, confident mistakes, latency and cost on retained cases before influencing workflow. Preserve explicit uncertainty and the existing evidence reviewer. |
| Shared acquisition and sources | Wire Crawlee to the engine; add document upload/parsing, source connectors, refresh/deduplication and clear collection budgets. | The selected source is actually read, retained and cited; unsupported, blocked, failed or stale sources remain visible. |
| Easier standalone setup | Supported install/launcher, model connection setup, document-engine setup, dependency checks, first-run sample, output location and actionable errors. | A fresh user follows the published setup and produces their first real document without developer intervention. Exact platform support follows tested builds. |
| Reliable recurring work | Public job contract/API, job queues, explicit resource/cost controls, recoverable execution and scheduled refresh where configured. | Another client can submit, observe, cancel and retrieve a job; restart does not duplicate effects or silently lose committed outputs. |
| MC integration | Same research-job contract through existing Link & Sync/plugin seams; scoped Canon/project inputs, visible progress, canvas access to actual documents, saved edits, governed knowledge handoff and implementation feedback. | A legitimate MC actor starts a job, uses its real output on canvas, saves/reopens it, and returns test evidence to the existing work records. Reconnect, cancellation and revocation are demonstrated. |
| Public launch and TMF funnel | Clear landing page, authentic downloadable examples, demo recordings, recognizable TMF branding, useful TMF next step, contribution/issue path and X/LinkedIn launch material. | A visitor understands the product, installs it, obtains a useful document and can find the TMF demo/contact path. Measure outcomes through voluntary feedback or disclosed opt-in measurement; no fabricated traction. |

## Delivery order

### 1. Finish the standalone document experience

Define native job/output contracts; improve editable templates; make the research
and document-engine setup understandable. Establish one repeatable research-report
example. This is the next work package, not a redesign of the research engine.

**Gate:** a fresh user can run a real research job and receive a useful, correctly
structured, editable file with source traceability and visible limitations.

### 2. Build prospect intelligence from domains and public sources

Add company/contact records, sourced opportunity analysis, offer-specific
qualification and real dataset/brief exports. Wire the shared collection path.
Explicitly validate each requested social/marketplace source before advertising
it. Add demand-discovery connectors incrementally rather than blocking public-web
prospecting on every platform.

**Gate:** a sourced sample for an agreed service and target market passes manual
contact, duplicate, opportunity and score audits. No invented budgets or needs.

### 3. Deliver knowledge packs that work in retrieval

Generate the readable pack and structured chunks from the same version. Preserve
evidence, scope, review state and supersession. Integrate with existing ingestion
owners; do not invent a competing knowledge catalog.

**Gate:** representative questions retrieve supporting passages with correct
citations, scope and freshness behavior. No TMF Brain Engine access.

### 4. Package and prove the free public release

Finish supported installation, model/document setup and three reproducible
showcases: sourced research, prospect intelligence and a useful knowledge pack.
Capture recordings and downloadable examples throughout stages 1–3. Evaluate
decision models alongside this work; no release depends on an unproven model name.

**Gate:** someone outside our setup can complete the advertised flows. Verify
downloaded documents and failures as well as the happy path.

### 5. Launch on X and LinkedIn

Publish the free tool, actual results and short demonstrations. Show how it helps
with a real problem; provide the repository, setup and a clear TMF next step.
Track installation problems, first useful outputs, repeat use, inquiries and
community feedback. Do not require an email gate or heavy advertising in client
deliverables as an unstated condition of the free product.

**Gate:** public claims match verified capabilities; users have a working path
from discovery to useful output and support.

### 6. Demonstrate the same job inside real MC

Integrate in parallel with the owning MC lanes when their seams are ready. Show
the same standalone job with shared context, agents, actual canvas documents,
connected workflows and saved results. Then introduce other MC features through
real work examples.

**Gate:** demonstrate the installed MC user path and persistent outcome. Source
code, an exported file or a canvas screenshot alone does not establish it.

## Later, separately scoped

Hosted accounts/team access/billing; additional providers; larger-scale monitoring;
CRM-specific integrations and delivery; richer collaboration. Dates, prices,
platform-wide access, customer outcomes and conversion lifts are not established.

## Next action

Implement stage 1's native job/output contracts and document templates, then the
stage 2 company/contact/evidence model. Keep this roadmap updated when an actual
acceptance gate passes; keep shared decisions and ownership in Canon.
