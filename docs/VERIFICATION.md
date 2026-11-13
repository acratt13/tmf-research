# Verification scope

2026-10-19, local macOS development environment.

- Core: 12 unittest cases passed on Python 3.14.6. Tests cover invented/missing references, partial/unavailable evidence, duplicate IDs, active markup, executive caveats and existing-output protection.
- Original JavaScript fixture: four Node assertions passed. It is synthetic and has no provider or database integration.
- Actual REA 6.7.0 invocation through this CLI: two JavaScript files parsed, zero skipped and zero parse failures. Evidence ID: `ev_27cb37699202e5e636f75bce85cd5fece7e60e6fc29c02603ca48a0789ed8833`. Full envelope generated locally; not redistributed because it contains local environment paths. Static analysis is not runtime execution.
- REA envelope import generated a report with no automatic findings and partial/unreviewed status.
- Markdown and escaped HTML generated from the sample JSON. PDF generated with the bundled ReportLab 4.4.9; extracted text retained requirements, caveats and evidence register. First PDF page was rendered and visually inspected. Whole-document typography, complex Unicode and every editor were not validated.
- Archify generated the proposed architecture: 9/9 deterministic showcase checks, no errors/warnings. Automated browser checks passed the tool's desktop matrix (1440×900, 1600×1000, 1920×1080 plus 2048×1320 coverage); largest dark screenshot visually reviewed. Initial taller candidate overflowed and was replaced by a separate compact candidate; failed evidence retained privately. This validates a design artifact, not the proposed runtime.
- Architecture specification SHA256: `ef26a309728819d2543c60384b6d40c1979eaa2f959d58b82b2bab4acc8f8c9d`. Delivered HTML SHA256: `c461791866d03db5d6b85f6fca1aa1173eb416a673dec54b6e66020e8a774778`.

This original foundation check did not test autonomous research roles, live search/fetch, hosted isolation, process-tree/resource containment, semantic claim verification, office/design adapter roundtrips, production provider operations or complete security assurance. Subsequent local Council implementation and live-run evidence are documented in [WORKBENCH.md](WORKBENCH.md). CI results are separate from local runtime evidence; model review remains distinct from independent factual verification.

Dependency risk is not established by successfully importing or using ReportLab. See its upstream/package advisories and your own dependency policy for a deployment decision.

Read-only dependency-reviewer package-risk lookup for ReportLab 4.4.9 could not run: the installed Endor CLI lacks the `agent` command. Dependency risk posture remains UNKNOWN; no package approval or security clearance is claimed. No package installation or Endor mutation was performed.


## Canon candidate bridge — 2026-11-13

Bounded source expansion on the existing `plugins/scrapling` branch, based on `ddb6f5c`. The authoritative expansion spec is Canon `cn-15d6a304-49db-42e9-8146-01d1ae576781`, revision 1, Phase 0 inventory and the first Phase 2 publication slice. The module/contract inventory and operator connection handoff are in README.

- Full Research suite: **125 tests passed, none skipped**, with `MC_CLI_SHIM` and `CANON_TEST_DIST` supplied; JavaScript syntax and `git diff --check` passed. The existing MC dynamic app show/put-away suite also passed 4/4 against its compiled code with scratch storage.
- Candidate tests execute actual local HTTP publication with synthetic source/review fixtures. They cover stable mission/source identities, original evidence labels, citation and exact source-revision retention, report snapshots, compare-and-set conflicts, repeated publication without new rows, missing authorization, partial connection failures, cancellation, restart and retry after lost receipts. The actual workbench process and original paged `result` CLI reconstruct the publication reference without starting a model or another research run.
- Optional native-contract acceptance uses the existing compiled MC Canon section writer and Knowledge declaration against temporary SQLite storage. The real writer accepted every candidate; repeat publication added zero rows. Changing the report kept the mission ID, advanced its revision to 2 and preserved the original report snapshot, adding only the new snapshot and mission revision. No live Canon knowledge fixture was written.
- Browser execution opened a retained synthetic partial result, clicked **Save candidates to Canon**, and read the resulting candidate publication state and mission revision 1. The research state remained partial. No JavaScript runtime error was observed; the sole console error was the existing missing favicon (404).
- The previously skipped shared-wrapper checks now run against the real external MC shim. The budget test's failure was caused by its fixture closing stdin before an asynchronous tool reply. Keeping the MCP session open through the reply fixes that test without changing the shared shim, the complete serialized-result assertion or the 2400-byte budget.
- No paid model calls, crawls, outreach, deployment, installation, push or live Research/MC restart was performed. Live Link & Sync provisioning and installed Canvas acceptance for this new adapter remain untested.

Reproduce the optional integration checks with the owning MC checkout's existing compiled backend and shared shim (paths supplied by the operator, never bundled into Research):

```sh
MC_CLI_SHIM=<shared-cli-shim.mjs> CANON_TEST_DIST=<backend-dist-src> python3 -m unittest discover -s tests -v
```

- Canvas handoff added after source inspection: the MC overlay uses its declared workbench service and native-view app card; both actor classes already share the generic `open_app` tool and dynamic put-away path. The baseline Research card does not whitelist a saved-run navigation query. Research now validates `?run=<id>` and opens that saved run; browser proof selected the requested run despite a different cached run ID. MC must add `query: ["run"]` to its existing card, replay the new Research commit through normal overlay ownership, and provision the authorized Canon connection. No Builder MC files were edited. Full installed dynamic-popup close/reopen and chat-switch/pin acceptance remain pending.


## Structured missions and actor controls — source expansion

The existing engine now accepts `tmf-research-mission/1` configurations and emits validated `tmf-research-intelligence/1` outputs. Company/startup briefing sections, inferred lead opportunities, market sections, profession knowledge, labeled person research and custom Council configurations all retain reviewed finding references. Actual model roles/collection/exports stay owned by the existing engine. Draft expertise is not a deployed Role or an agent.

Synthetic engine and HTTP tests cover each mission type, separate mission-output review and withholding, domain scope before HTTPS redirect contact, scoped Scrapling collection without uncontrolled browser redirects, original evidence labels, unknown/partial output, company-domain deduplication/conflicts, model/source budgets, custom responsibilities, pause/resume of one active controller, owned crawler cancellation, and refinement of hash-checked crawler snapshots. Profession publication produces independently addressable knowledge, one collection and expertise pointing to its exact revision. Two readers consume the same Canon revision with no duplicate knowledge writes. Scoped knowledge reads reject other namespaces and missing revisions.

The existing four lifecycle operations are preserved. Companion tools are `publish`, `missions`, `pause`, `resume` and `knowledge`, all declared through the same generic CLI shim, allowlist and read-only annotations. No additional MCP server, knowledge store, scheduler or runtime is added.

Browser execution with synthetic fixtures selected a profession mission, reviewed its brief, ran the same research controller, read the structured candidate expertise with source links and published the collection/definition into isolated Canon fixtures. The original report and model-review limitations remained visible. This is a UI/backend flow proof with synthetic evidence, not quality acceptance for a real profession or installed MC acceptance.

Durable restart-stage resume, actual Hub expertise-socket import/agent deployment, full person simulation runtime, automatic knowledge promotion/recurring missions and distributed workers remain unimplemented. The README phase matrix keeps these gaps explicit. Source support is not installation proof; installed evidence is recorded separately after the normal plugin update.

Source validation before installation: full suite **149 tests passed, zero skipped** with the real shared CLI shim and compiled Canon writer supplied; JavaScript syntax and diff checks passed.
