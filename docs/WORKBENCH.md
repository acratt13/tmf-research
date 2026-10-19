# TMF Council local research workbench

TMF Council is the research team. A lead creates a bounded plan; a source scout finds public primary sources; specialists investigate different questions; the REA adapter inspects explicitly selected local artifacts. An evidence reviewer challenges claims, advisory perspectives identify consequential gaps, follow-up investigation gathers more evidence, and a synthesis lead creates the selected deliverables. A final model review can withhold unsupported synthesis.

## Start

Python 3.11+ and an installed, authenticated Codex CLI **0.160.1** are required for live model roles. The role adapter ignores user CLI configuration/rules, suppresses skill discovery, disables plugins/apps/hooks/shell and other tool features, uses fresh ephemeral temporary working directories and read-only execution, and enables native web search only for the source scout. Existing authentication stays in its normal provider location; the project does not read or copy credential files. No model name is forced. This version check is intentionally strict; supporting another CLI needs a fresh capability/isolation check.

```bash
python3 -m tmf_research serve
```

Open `http://127.0.0.1:8765`. The service binds only to loopback and checks Host/Origin and a per-session request token. It has no public sharing or tenant authentication. Do not expose it through a reverse proxy as a hosted service.

For configured engines, edit a private copy of `examples/workbench-config.json`, replacing placeholders with actual local executables and targets. Store it under ignored `runs/` or `.private/`.

```bash
python3 -m tmf_research serve --config runs/local-config.json
python3 -m tmf_research run examples/research-brief.json --config runs/local-config.json
```

Use absolute paths in operator configuration. Commands are argument arrays, never model-generated shell text. The server accepts only configured REA target IDs; a webpage cannot select a local file or executable. Without optional engines, Markdown/HTML/builder exports still work. PDF uses configured WordCraft or optional ReportLab. The application does not download software or install dependencies.

## Intake and research lenses

The subject and intended decision form the question. Select any combination of Understand, Compare, Build, Audit and Offer a service. Context records audience, geography, industry, constraints and known unknowns. Starting URLs are optional leads, not automatic evidence. Depth selects bounded source/round/model-call limits:

| Depth | Web source attempts | Follow-up rounds | Model calls |
| --- | --- | --- | --- |
| Quick | 4 | 0 | 14 |
| Detailed | 8 | 1 | 24 |
| Deep | 12 | 2 | 32 |

Up to three independent specialist role calls run concurrently. Council perspectives also run with concurrency three. These are maxima, not promises to spend the full budget. Each Codex call has a 180-second deadline; expensive native web-search activity can occur within that call. Call limits are **not** hard monetary or total-token caps. Usage is recorded where the CLI supplies it; dollar cost remains unknown. One workbench job runs at a time.

Review the combined brief before starting. Presentation choices are separate: Markdown, HTML, PDF, DOCX, XLSX, PPTX, proposed workflow diagram and a structured builder package. The TMF Service Blueprint preset selects all lenses, deep research and all formats. Changing input invalidates the preview.

## Evidence and disagreement

Search results are leads until fetched. A source snapshot records retained-byte SHA256, requested/final URL, content type, charset, retrieval time, availability and truncation. HTML is parsed inertly. Analysts get bounded excerpts; the full retained response and extracted text remain local. The HTTPS transport pins a validated public address with hostname TLS checks, revalidates redirects, ignores environment proxies and applies a socket wall deadline. OS DNS resolution retains the system resolver's timeout.

Selected REA operations retain the evidence envelope, exact saved-envelope hash, version-dependent provider metadata and limitations. The provider receives bounded summaries/graphs with common local-path/secret-key fields redacted. Redaction is not a guarantee that arbitrary artifact content is nonsensitive. **Selected local REA excerpts are sent to the model provider**, alongside the brief and public passages; select only material intended for that transfer.

Factual findings need a known available/partial source and a short exact supporting passage to enter review. Quote matching is only structural admission. A separate role checks entailment against surrounding original context. Unsupported/uncertain claims remain in the local claim ledger and become explicit gaps; they are excluded from accepted findings. A partial source never becomes runtime or completeness proof. Requirements are proposed and include acceptance conditions; their evidence-basis references cannot point to unavailable sources.

The Council adds customer, delivery, operations/economics and assumptions perspectives plus up to two subject-specific perspectives selected by the lead. These are simulated same-provider advisory roles. Raw positions, risks, alternatives and evidence requests are retained. The synthesis must preserve the strongest dissent; confidence is subjective, not a factual verification score. Council opinions cannot approve a factual claim by vote.

Material reviewer/Council objections feed bounded follow-up research. Source-budget exhaustion or failed retrieval leaves a visible gap. The objection ledger retains initial requests conservatively; it is not a complete task-by-task closure proof. Final synthesis receives another evidence review with the material gaps. If rejected, the application withholds its narrative, title, new requirements and workflow, falling back to reviewed findings and earlier validated proposals. No unsupported diagram is silently delivered.

## Persistence and recovery

Each run has a UUID directory containing its brief, plan, search results, retained source bodies/text, REA evidence, specialist results, claim decisions, raw Council positions, synthesis/review, outputs, receipts and role-call/usage metadata. JSON state saves use flush/fsync and atomic replacement. Files are local and **not encrypted by this project**. They may contain confidential research; keep the run directory private.

Statuses distinguish queued/running, completed, partial, failed, cancelling, cancelled and interrupted. Completed means the configured investigation finished with accepted findings and requested outputs; it is not comprehensive knowledge, independent certification or implementation acceptance. Partial exposes unavailable exports, acquisition failures or unsupported claims. A failed job retains evidence; the UI never turns it into an empty success.

Cancellation prevents later stages/publication. An in-flight bounded provider/renderer operation may finish before cancellation is observed. POSIX subprocess deadlines/output limits kill and reap the child process group; Windows cleanup is limited to the direct process. Restart marks unfinished jobs interrupted, including pending cancellation, without automatically replaying work. Automatic resumable execution is not implemented; use retained evidence and start a new run.

## Exports

Markdown/HTML share the report renderer. PDF uses WordCraft when configured or ReportLab when installed. WordCraft produces editable documents with saved-text checks; GridCraft exports requirements, evidence and unknowns, protecting research text from being interpreted as formulas. DeckCraft includes evidence/caveats in speaker notes and bounds visible slide text. Configured `craft.designcraft` (tested CLI 0.9.0) produces an editable `.designcraft` document, script, PDF and PNG from the accepted workflow. It checks saved story lengths, text overflow and zero-issue preflight; oversized content fails explicitly. The template supports two to six steps. When DesignCraft is absent, the legacy Archify adapter requires showcase validation/delivery. The builder JSON includes the report, analysis, claim decisions, plan and raw Council positions.

Export failures are per-format, never fabricated successes. Receipts pin generated artifacts to the report revision. Native editor operation, actual Microsoft interoperability, arbitrary complex layouts and unattended production delivery are not established by file generation.

After a run, choose other formats and use **Export this research in selected formats**. The application reuses the retained published analysis and accepted report, preserving the original files and creating a separate export revision. It does not rerun research roles or reuse a rejected synthesis draft. Older development runs without a retained published analysis cannot use this path.

## Scope still outside this release

Hosted tenancy, automatic database ingestion, private email access, local PDF/document uploads, cross-provider review, complete gap-closure tracking, automatic resume, hard monetary budgets and a controlled quality benchmark against ordinary search remain outside this implementation. Current role review can still be wrong. Human/source review remains necessary before making client promises or shipping a system.

## Live verification

See the [actual integrated customer-service run](../examples/council-live/README.md) for generated artifacts, role/search counts, timings, usage, withheld claims and presentation limits. The preceding manual study and Office-only trial are separate examples. The current regression suite has 37 tests, including quote admission, missing/negative reviews, rejected-synthesis fallback, process limits, private-address rejection, cancellation/restart, local request guards and accepted-revision re-export.
