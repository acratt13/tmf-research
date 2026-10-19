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
