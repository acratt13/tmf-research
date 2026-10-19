# Research workbench specification

Version 0.1 · Proposed architecture. See README for implemented scope.

## Product job

Turn a broad question or buyer request into a traceable investigation, software breakdown and useful deliverables. Example: “What must a premium customer-service platform include?” Produce the operational workflows, data, permissions, integrations, security applicability, failure cases, acceptance tests, unknowns and sources needed to scope a real system.

The differentiator is a connected web/document/software-inspection pipeline with reusable evidence and multiple output views. This does not establish parity with Perplexity or reveal its private implementation.

## Roles and shared state

A research lead owns scope, budget, task queue, research depth and stopping conditions. Specialist roles use bounded inputs and separate working contexts:

1. Planner: decomposes the question, region/version constraints and required evidence into research tasks.
2. Web researcher: finds primary sources, follows references, records dates and compares competing claims.
3. Document researcher: analyzes explicitly selected files, preserves document/page locations and confidentiality.
4. REA analyst: selects permitted inspection operations against accessible demos, SDKs, bundles or authorized targets. Keeps original evidence IDs, hashes, coverage and limitations.
5. Reviewer: checks claims against source passages and artifacts, seeks counterexamples, distinguishes contradictions from version/region differences, and requests follow-up research.
6. Writer: builds a structured report and audience-specific views from reviewed findings, preserving gaps and caveats.
7. Presentation adapters: render the accepted report revision into Markdown, PDF, Archify diagrams and supported editable document/deck/sheet/design formats.

The roles are tasks with explicit contracts; not every question needs a separate process or model for each. Parallelize independent investigations within configured budget/concurrency. Review must inspect originals rather than merely ask another model whether a summary sounds right. Runtime research agents do not become software builders or acquire shipping authority.

Shared records: ResearchRun, Task, Source, FetchAttempt, Artifact, Observation, Claim, Citation, Contradiction, Requirement, AcceptanceCase, ReviewDecision, ReportRevision and ExportReceipt. Every record has a stable ID and run/client ownership. Store evidence outside model context; retrieve bounded relevant sections rather than passing every source to every role.

## Research loop and completion

Scope → plan → retrieve/inspect → register evidence → extract bounded claims → review → investigate material gaps → synthesize → human review where needed → export. Stop when required questions have evidence or explicit unknowns, and the reviewer has evaluated the critical claims; otherwise stop on budget/cancellation and label the result partial.

Runs support queued, running, waiting-for-access, reviewing, partial, completed, failed and cancelled states. Preserve progress and failure evidence. Resume must reconcile ongoing provider work and external effects before repeating actions. Report research coverage separately from whether the process itself completed.

## Evidence requirements

Each source records origin, retrieval time, effective/publication date if known, exact product/region/version, content hash or artifact digest, location, access state, coverage and limitations. Each claim records evidence label, source locations, supporting and opposing evidence, review state and unresolved questions.

Evidence labels: documented, observed, inferred, proposed, unknown. “Observed” includes the actual context: static metadata observation is not runtime workflow execution. Search snippets are leads until the source is read. A citation reference resolving is a structural check, not proof that the cited source entails the claim. Independent semantic/source review remains necessary.

Do not convert model confidence into factual verification. Distinguish absent, unreadable, inaccessible, stale, contradictory, valid-empty and not researched. Conflicts survive into the report until resolved with explicit rationale. Document date-sensitive claims and refresh policies.

## REA integration

Use the real REA CLI/MCP behind an adapter; do not reimplement or rename its engine. Record installed version, exact operation/parameters, target identity, environment, original envelope, evidence ID, coverage, omissions, warnings and failures. Some tools return a partial/error result with exit code zero; read the envelope rather than treating the process exit as coverage proof.

Start with static local artifact inspection. Runtime browser/native tests are a separately authorized mode with isolated sessions and sample data where possible. Public demo behavior must remain distinct from production behavior. Do not infer internal models from wrapper plumbing or field presence. Inspection cannot grant credentials, licensing, production authority or private source access.

Bound runtime, output, memory and concurrency per operation. A timed-out or resource-exhausted worker produces partial/failed evidence with an explicit reason. For large artifacts, select exact files/types and preserve selection limits rather than silently omitting material.

## Model and retrieval adapters

Keep provider interfaces separate: plan(tasks), search(query, filters), fetch(source), inspect(target, operation), review(claim, evidence), synthesize(records), export(report). Record provider/version, budgets and failures. Allow provider substitution without changing the evidence contract.

Public research should not inherit private email/client context. Explicitly select which documents can leave the machine for a model provider. Treat source text as data and prevent retrieved content from issuing executable commands, changing destinations or requesting secrets. Separate untrusted URLs and provider endpoints; enforce redirect/network/file permissions for a hosted deployment. Secrets stay in the chosen secret manager, referenced by name.

No provider integration is declared available merely because this document lists it. Current official examples informing the design include Perplexity's public search/agent platform and its Search as Code architecture. [Platform](https://www.perplexity.ai/api-platform), [Technical architecture](https://www.perplexity.ai/hub/blog/rethinking-search-as-code-generation). These are vendor descriptions, not independent benchmark verification.

## Output choices

One canonical research record drives all views:

- Executive brief: key conclusions, choices, risk and unresolved decisions.
- Full research report: methods, sources, findings, contradictions, scope and limitations.
- Builder specification: capabilities, workflows, states, records, interfaces, business rules, dependencies and executable acceptance cases.
- Architecture/process/data/state diagrams: relationships must link back to finding or requirement IDs.
- Client proposal inputs: outcomes, scope, dependencies, delivery phases and acceptance—not fabricated savings or unsupported prices.
- Reusable knowledge pack: chunkable domain guidance with source metadata and caveats retained.

Formats: Markdown and JSON; self-contained HTML; PDF; Archify HTML/SVG and supported image export; editable document/deck/spreadsheet/design formats through individually verified adapters. An export receipt records report revision, renderer/version, artifact hash, format, evidence references and validation/open-readback result.

Archify is the proposed diagram renderer; its skill-generated architecture artifact in docs is a design, not proof of an implemented multi-agent runtime. WordCraft (Word-style reports), GridCraft (Excel-style workbooks) and DeckCraft (PowerPoint-style decks) are the primary proposed Office adapters, as clarified by the project owner. Their official repositories document CLI/MCP control and dual MIT OR Apache-2.0 code licensing; see OFFICE-ADAPTERS.md. Their runtime adapters are not implemented. Exact releases, bundled-asset/branding conditions and open/edit/save/reopen/export paths still require verification. Adobe-style editors remain separate candidates. Do not bundle proprietary assets or assume a clone supplies format fidelity.

Edits in a presentation tool create a derived revision and record provenance. Never silently rewrite the research ledger from a styled document. Regeneration must show whether manual edits would be replaced. Citation/unknown retention is required even in short executive views.

## Acceptance and evaluation

Use synthetic fixtures and public/permissioned examples. Test factual source support, citation/location accuracy, contradictory-source handling, version/region fidelity, source freshness, access failures, prompt injection, privacy boundaries, coverage honesty, cost and time. Measure completed research tasks and useful reviewed requirements rather than page count or agent count.

For REA, replay known complete/partial/failure outputs and run at least one actual selected artifact inspection. For exports, verify citations and caveats survive Markdown/HTML/PDF, open artifacts, inspect pagination/readability, and verify editor save/reopen. Do not report a document connector as working from a menu entry alone.

## Current implementation and remaining work

Implemented: local report contract validation; evidence-labeled Markdown/HTML export; optional PDF export; selected REA CLI invocation; conservative REA envelope import. Validation is structural; it does not verify claim truth. Local commands do not form a hosted service or secure sandbox.

Not implemented: autonomous planner/researcher/reviewer roles; live search/fetch adapters; iterative investigation; durable run orchestration; semantic claim verification; browser/native REA orchestration; Archify runtime adapter; editable office/design adapters; GUI; hosted multi-client service; automatic knowledge-base ingestion.

First vertical slice to build next: one software question → bounded primary-source search → one selected real REA inspection → reviewed claim ledger → detailed specification → Markdown/PDF/Archify views. Complete the privacy, cost and recovery tests for this slice before broadening provider support.
