# TMF Research

[![Tests](https://github.com/acratt13/tmf-research/actions/workflows/test.yml/badge.svg)](https://github.com/acratt13/tmf-research/actions/workflows/test.yml)

**Research the system. Inspect the software. Keep the evidence.**

An open workbench for turning research and software inspection into useful, traceable specifications—not just another long answer.

**Local workbench, early release.** TMF Council connects a research lead, source scout, specialist investigations, real REA inspection, evidence review, critical perspectives, follow-up research and selected exports. Roles are separate bounded calls through the user's installed Codex CLI, not independent human experts. Read the [setup, evidence boundaries and live-run verification](docs/WORKBENCH.md). This is not a hosted service or a proven improvement over ordinary search.

The [intelligence and production bundle](docs/INTELLIGENCE-PRODUCTION-BUNDLE.md) keeps the full scope together: collection, design, professional software, client intelligence, knowledge, documents and MC handoffs, with explicit evidence boundaries.

See [what works today and the delivery roadmap](docs/ROADMAP.md) for the path to specialized documents, prospect intelligence, RAG-ready knowledge packs and Mission Control integration.

![Proposed research architecture](docs/architecture.png)

## Try it in one minute

For the research workspace, use Python 3.11+ and an authenticated **Codex CLI 0.160.1**. The exact CLI boundary is checked; other versions fail visibly rather than silently weakening role isolation.

```bash
python3 -m tmf_research serve
# Open http://127.0.0.1:8765
```

Choose any combination of **Understand / Compare / Build / Audit / Offer a service**. Choose depth and outputs, review the brief, then start. The **TMF Service Blueprint** preset selects all lenses and formats. Optional Craft/Archify exports and REA targets require local operator configuration; missing engines produce explicit partial results. Start with Markdown, HTML and the builder package for a dependency-free presentation path.

For command-line research, see [example brief](examples/research-brief.json) and [configuration](examples/workbench-config.json). Run files and evidence stay under ignored `runs/` by default. Selected brief, public passages and local REA excerpts are sent to the model provider; select only material you intend to share.

### Short workbench lifecycle commands

The workbench above remains the only job owner. These commands contact that running service and exit promptly; they do not launch another worker or run the model inside a tool call. The operator can set `TMF_RESEARCH_URL` to another `http://127.0.0.1:<port>` before launching the CLI. Actors cannot select configuration, credentials, a service URL or executable through command arguments.

```bash
python3 -m tmf_research status
python3 -m tmf_research submit --request-id example-intake-001 --brief-json '{"question":"What makes webhook intake reliable?","depth":"quick","formats":["md","html"],"council":false}'
python3 -m tmf_research status --id <returned-run-id>
python3 -m tmf_research result --id <returned-run-id>
python3 -m tmf_research cancel --id <returned-run-id>
```

Reuse the **same request ID and brief** after a lost response. It returns the same saved run, including cancelled, failed or interrupted runs; it never automatically restarts work. A different brief with that ID, or a different request while a job is active, is refused. Cancellation reports `cancelling` until the existing worker stops. Standalone `run`, `refine` and `serve` behavior is retained. Operator-managed provider authentication stays with the workbench; the CLI holds its local workbench token in memory only.

Status/results are valid JSON envelopes containing a bounded text range of the original JSON document, its `content_type`, character cursor, total length and SHA256. Continue with `--cursor <next_cursor> --sha256 <sha256>`; a changed document is refused instead of mixing revisions. `next_cursor:null` is the end. Reassemble `text` ranges before parsing that document. The complete MCP result (including `isError`, the pretty-printed CLI response and the existing text wrapper) stays within 2400 bytes; an HTTP read is capped at 8 MiB. Larger originals remain with Research. Result references name the original exports; partial, failed, withheld and interrupted evidence is not upgraded into success.

The packaged `tmf_research/mc/mcp-servers.json`, `mc/allow.json` and `mc/tool-annotations.json` are standard metadata inputs for MC's existing generic CLI wrapper/install owner: four commands only; status/result read-only, submit/cancel mutating. They are **not** a new MCP server or transport and do not establish an installed connection by themselves. The shared CLI shim belongs to MC, not this repository. The declared invocation ends in `-- tmf-research`, the console entry in `pyproject.toml`; its generated names are `tmf-research_submit`, `tmf-research_status`, `tmf-research_result` and `tmf-research_cancel`. Apply the declaration and matching annotations together instead of substituting an automatically recognized launcher. The wrapper source is supplied by the existing MC import owner, not copied into Research source. Applying those inputs, repairing its generic wrapped-help parser, role/profile grants, governed tool execution and installed acceptance are the separate MC integration slice. No model job, provider compatibility or installed MC acceptance is claimed by these CLI tests.

### Existing evidence/report commands

Python 3.11+. Core commands have no third-party Python runtime dependencies.

```bash
git clone https://github.com/acratt13/tmf-research.git
cd tmf-research
python -m tmf_research validate examples/report.json
python -m tmf_research render examples/report.json --format md --output runs/report.md
python -m tmf_research render examples/report.json --format html --output runs/report.html
```

Open `runs/report.html` in your browser. Existing output files are protected from silent replacement; choose a new output name when regenerating.

The [example report](examples/report.md) uses an original synthetic payment-allocation fixture, not private client material or a claim about a commercial product. Compare the same record as [PDF](examples/report.pdf), [HTML](examples/report.html) or [JSON](examples/report.json).

Optional PDF export:

```bash
python -m pip install '.[pdf]'
python -m tmf_research render examples/report.json --format pdf --output runs/report.pdf
```

Use `--audience executive` for a shorter view. Caveats, unknowns and the evidence register remain in both views. PDF currently uses ReportLab's default core fonts; complex-script/complete Unicode typography is not established.

## Actual Office-engine trial

**Research quality direction:** [ChatGPT, Perplexity and Crawlee comparison](docs/DEEP-RESEARCH-COMPARISON.md) separates documented patterns, current engine gaps and proposed upgrades with acceptance evidence.

**Decision-model trial:** [Evaluate Perplexity Flash and Standard](docs/DECISION-TRIAL.md) on labeled work routing, research depth, output selection and evidence checks. Advisory only; requires a separately provisioned API credential. This does not replace the research reviewer.

**Integrated Council run:** [Read the generated research and verification](examples/council-live/README.md). Seventeen role calls, actual source retrieval and REA inspection, six critical perspectives, follow-up research, 16 accepted findings and 14 proposed requirements. Three uncertain claims were withheld; the example remains partial, with a separately verified DesignCraft workflow export.

**Real service study:** [Customer-service automation pilot](examples/customer-service-study/README.md) — official vendor research and actual REA SDK inspection turned into a build blueprint, 32 acceptance requirements, editable Office files and an interactive workflow. Research was operator-assisted; the repository did not autonomously investigate the subject.

WordCraft, GridCraft and DeckCraft v0.8.0 created, reopened, edited and exported an original service-readiness briefing. [See the trial and download DOCX/XLSX/PPTX/PDF outputs](docs/CRAFT-TRIAL.md). This is a reproducible local engine test, not an implemented autonomous research pipeline.

![DeckCraft-generated briefing](examples/craft-trial/presentation-preview.png)

## Real REA integration

[REA](https://github.com/morluto/rea) is an independent open-source reverse-engineering project. Install/build it using its own instructions. TMF Research calls the actual CLI and retains its evidence envelope; it does not replace the engine.

With `rea` on your PATH:

```bash
python -m tmf_research inspect examples \
  --operation analyze-javascript-application \
  --output runs/rea.json
python -m tmf_research import-rea runs/rea.json \
  --title 'Payment fixture inspection' \
  --output runs/rea-report.json
python -m tmf_research render runs/rea-report.json \
  --output runs/rea-report.md
```

For a source checkout, supply `--rea-command '["node", "/path/to/rea/scripts/rea.mjs"]'`. No shell evaluates this command prefix. Supported operations: `inspect-managed-artifact`, `inspect-managed-members`, `analyze-javascript-application`. Default timeout: 60 seconds, configurable up to 300.

Import deliberately starts with **zero asserted findings** and partial/unreviewed evidence. Read the original result, coverage and limitations before writing domain claims. REA returning a process exit code of zero is not proof of complete inspection. A static SDK field is not an executed workflow.

## What exists today

| Capability | Status |
| --- | --- |
| Report contract and source-reference validation | Implemented; structural checks only |
| Finding labels: documented / observed / inferred / proposed / unknown | Implemented |
| Markdown and escaped, self-contained HTML | Implemented and generated/read locally |
| PDF | Implemented via optional ReportLab; generated, text-read and first page visually reviewed |
| Explicit local REA invocation and conservative import | Implemented; real JavaScript fixture inspection run with REA 6.7.0 |
| Proposed architecture diagram | Generated with Archify; artifact and bounded desktop-browser checks passed |
| Lead, scout, specialist, reviewer, Council and writer roles | Connected local role calls; same-provider model review, not factual certification |
| Iterative web search/fetch and retained source evidence | Native web-search events checked; bounded HTTPS snapshots and selected follow-up research |
| Workflow export adapters | DesignCraft editable document, PDF and PNG with preflight checks; legacy Archify showcase adapter |
| WordCraft / GridCraft / DeckCraft outputs | Configurable local CLI adapters; document/workbook readback and citation/caveat preservation; native GUI/Microsoft interoperability not established |
| Research UI and durable runs | Loopback workbench, composable lenses, preset, live stages, result files and saved history |
| Hosted multi-client service, document uploads and automatic KB ingestion | Not implemented |

The validator checks required fields, reference integrity, evidence availability and visible partial-source caveats. **It cannot establish whether a claim is true or entailed by a source.**

## Where this is headed

A lead researcher coordinates bounded specialists for web research, selected documents, REA inspection, evidence review and report assembly. They share a versioned evidence ledger. Presentation adapters produce executive briefs, detailed research, build specifications and diagrams from the same structured record.

- [Actual Craft trial and editable output files](docs/CRAFT-TRIAL.md)
- [Open-source Office adapter comparison](docs/OFFICE-ADAPTERS.md)
- [Research workbench specification](docs/RESEARCH-WORKBENCH-SPEC.md)
- [Professional services specification](docs/SERVICE-SPEC.md): 14 offer families, delivery requirements, acceptance, support and assurance applicability
- [Interactive architecture](docs/architecture.html): download and open locally
- [Contribution guide](CONTRIBUTING.md)
- [Security and privacy boundaries](SECURITY.md)

Useful first contributions: report-contract edge cases, citation-preserving exports, source/provenance adapters, or a bounded search→review→spec vertical slice. Start with an issue for larger architecture changes. No fake provider-success paths or production claims based on fixtures.

## Verification

```bash
python -m unittest discover -s tests -v
node examples/check-payment.mjs  # optional: exercise the original JS fixture
```

Initial local evidence: 12 report/validation tests, four synthetic JavaScript assertions, an actual REA inspection (two JavaScript files parsed; none skipped; no parse failures), and generated Markdown/HTML/PDF with PDF text readback. These are bounded checks, not a full research-agent benchmark. See [verification notes](docs/VERIFICATION.md).

## Credits and license

Optional [remote Crawlee collection plugin](plugins/crawlee/README.md): bounded public HTML acquisition, saved evidence passages and JSON/Markdown source packs over SSH. See the [role knowledge-pack contract](docs/KNOWLEDGE-PACKS.md) for the proposed review and KB integration layer. Collection and operational approval remain separate.

MIT for original TMF Research code. [REA](https://github.com/morluto/rea) supplies the external inspection engine. [Archify](https://github.com/tt-a1i/archify) generated the proposed architecture viewer. See [third-party notices](THIRD_PARTY_NOTICES.md). No affiliation with Perplexity, Adobe or Microsoft is implied.

The optional cross-repository wrapper check runs the actual shared MC shim: set `MC_CLI_SHIM` to that installed source and run `python3 -m unittest discover -s tests -p test_mc_wrapper.py -v`. It checks generated console names, the four-operation allowlist and the real MCP result serializer. It uses a synthetic CLI fixture; it does not claim installed Research integration.
