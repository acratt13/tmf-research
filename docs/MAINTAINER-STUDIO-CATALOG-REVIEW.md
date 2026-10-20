# Maintainer and Kit Studio: ecosystem source review

Reviewed 2026-10-20. This is a source-backed reuse map for discussion. No candidate was installed, built, enabled or exercised by this review. Compatibility with MC is untested.

## The three repositories are different resources

| Repository | Pinned commit | What was examined | Best use |
|---|---|---|---|
| [Alex-Yanggg/awesome-DSH-plugin](https://github.com/Alex-Yanggg/awesome-DSH-plugin) | `3b44fe8ffddbf19ccebd459829e5a8ae2cbb0fa6` | 11 tracked files inventoried; README, structured catalog/schema and generation machinery inspected; 85 structured catalog rows parsed | Compact technical discovery and scaffolding/manager leads |
| [walkinglabs/awesome-deepseek-harness-plugins](https://github.com/walkinglabs/awesome-deepseek-harness-plugins) | `f1bfd6a172d795fa6ed5200a175f415dc6acd180` | 8 tracked files inventoried; documentation and inclusion guidance inspected; 258 bullet catalog/resource rows parsed; eight Mermaid diagrams identified | Architecture, lifecycle, profile and verification guidance |
| [awesome-dsh-plugin/awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin) | `80ef5aef034165f4793f77ec911218bed7b57121` | 6,417 tracked files inventoried; all 6,253 plugin YAML records parsed; selected normalization, index and capability-scanning source inspected | Broad discovery plus automated catalog maintenance |

These counts have different units. Resource rows are not all installable plugins, and parsing a record is not auditing its linked implementation. All tracked files were hashed for the local inventory; selected source was read. This is not a claim of reviewing every linked project.

The large catalog is mostly records, generated README content and supporting scripts. Its CC0 catalog license does not grant rights to the code of every listed plugin.

## What we should reuse

| Job | Candidate and source evidence | Recommendation and limit |
|---|---|---|
| Create plugin skeletons | [dsh-suite scaffolder](https://github.com/whyihaveyou/dsh-suite/tree/56765995db80fca9e6676da160b136277c68a3fe/packages/create-dsh-plugin): templates for tools, events, WebUI, panels and preset packs; `src/verify.js` builds, installs to a temporary profile and checks composed config | Strong Studio building block. Its verification ends at config presence; MC still needs runtime tool and canvas acceptance. Suite root is a repository, not one installable plugin. |
| Diagnose broken plugins | [PerryLink Doctor](https://github.com/PerryLink/dsh-plugin-doctor/tree/ba3f531d46158f3ab1f6170a951405637cac47ed): `lib/framework.mjs`, package/Cordis/runtime checks and `lib/checks-smoke.mjs` | Strong Maintainer trial candidate. Structured results distinguish static checks, dynamic smoke and degraded host-contract coverage. Dynamic checks can execute code; a skipped check must remain visible. Apache-2.0, package 0.7.4. |
| Install, smoke and test a capability | [PerryLink Test Drive](https://github.com/PerryLink/dsh-test-drive/tree/6fdcdfaee8b539858bc59888267889da584dee0a): `src/drive.ts`, `src/workspace.ts`, README host restriction and result schema | Strong isolated qualification candidate. Separates boot smoke from observed capability. Needs a CLI able to start a second headless process; the DSH Desktop launcher is explicitly unsupported as the test host. Temporary DSH homes are not an OS security sandbox. Apache-2.0, package 0.3.22. |
| Security and provenance triage | [security pack](https://github.com/PerryLink/dsh-skill-pack-security/tree/edb9f79856e3a007bbe9ccda1199337d7b94c102): `provider/src/vet/engine.ts`, checks/scanners and source/fetch modules | Trial its structured checks for license, commit/source, dependencies, install scripts and suspicious patterns. A weighted score is triage, not proof of safety. Preserve skipped/unknown dimensions; the engine assigns unknown dimensions a numeric default. Apache-2.0, root package 2.2.24. |
| Find combinations and conflicts | [Autocompose](https://github.com/Han-1413141/dsh-autocompose/tree/563fe9b4c9b1ee85439ae73da6c98f49cd6ec74e): `src/planning.ts`, `src/planner.ts`, `shared/compatibility.ts` | Useful compatibility/planning implementation: version, platform, embedded runtime, missing dependencies, declared conflict and duplicate service/tool checks. It composes plugin selections/profiles; it does not establish source-part fusion into one new plugin. Package 0.5.0 pins DSH 0.2.0-rc.2 peers. MIT. |
| Registry, discovery and installed-state UI | [vlln registry console](https://github.com/vlln/plugin-registry/tree/7309b958980dc66e671ecad5374b8d1469b494d9/packages/plugin/console), especially `src/index.ts` and `src/discovery/`; [suite manager](https://github.com/whyihaveyou/dsh-suite/tree/56765995db80fca9e6676da160b136277c68a3fe/packages/plugins/plugin-manager) | Compare useful discovery/inspection pieces, then choose one approach. Both have mutation paths that need reconciling with MC ownership: registry console writes profile patches and manages packages; suite manager invokes DSH install/update commands. Do not activate both as competing install authorities. |
| Scheduled ecosystem upkeep | [suite compatibility pipeline](https://github.com/whyihaveyou/dsh-suite/blob/56765995db80fca9e6676da160b136277c68a3fe/scripts/compat-check.mjs); [community capability records](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin/blob/80ef5aef034165f4793f77ec911218bed7b57121/scripts/lib/capabilities.mjs) | Reuse layered metadata/install/config checks, bounded schedules and version-sensitive evidence. Community capability facts retain prior evidence on failure and invalidate changed releases. Neither config assembly nor a static scan proves a usable canvas workflow. |

Other discovered leads include plugin-upgrade, harness-ops, plugin-kit, build-control and browser verification projects. Those remain catalog leads, not source-qualified recommendations in this review. Identical names occur under different owners: always retain repository owner, package identity and commit.

## Shared product scope

**Kit Studio** inspects donor plugins, maps reusable parts and overlaps, plans combinations, runs experiments, and creates a new packaged plugin. It should show the evidence, edits and results on the canvas. Existing Kit Studio remains the composition core to inspect and extend; Autocompose is a possible planning input.

**Maintainer** owns plugin operations across that product: intake, catalog enrichment, qualification, install readiness, updates, security checks, repair, regression checks, deprecation and escalation to builders. Existing Maintainer jobs and request/fit queues remain the starting point.

**MC host owners remain authoritative:** Link & Sync for connections/install/lifecycle, EMS for settings, existing profiles for Agent/Builder assignments and grants, and the existing canvas/artifact stores for displays and saved work. A reusable tool can perform an operation through that owner; it must not silently establish a second owner or settings store.

## Bounded first qualification stack

Start with the existing MC Maintainer and Kit Studio, then trial Doctor, Test Drive and the security vetter as complementary checks. Trial the scaffolder for Studio output. Evaluate Autocompose compatibility logic separately against the actual installed DSH version. Keep catalog discovery as a feed into existing intake; postpone installing another full manager UI until its mutations are mapped.

The custom work is the integration: normalize these tools' reports, call them through existing jobs, preserve exact artifact identities, distinguish unknown/skipped from passed, display results in the canvas, and pass qualified packages to Link & Sync. We should not write replacements for each tool.

## Proof gates before adoption

1. Pin each candidate and inspect its published artifact, dependencies, license and supported host version.
2. Run diagnostics against a real plugin and a known broken fixture; retain raw findings and skipped coverage.
3. Exercise isolated install → load → named tool invocation → uninstall/cleanup using an appropriate CLI test host.
4. Through MC, exercise assignment/grants → runtime loading → tool → editable canvas result → save/restart/reconnect → disable/remove. Confirm grants remain separate from installed executable code.
5. For Studio, combine identified reusable parts into a newly named plugin, retain attribution and license requirements, build and qualify that actual output. Profile composition alone does not pass this gate.
6. Prove update/repair failure preserves the last working version and user state. A judge can prioritize experiments; it cannot substitute for these results.

## Live snapshot and limits

Earlier in this review, live MC reported Maintainer `enabled:false`; its latest ten recorded security runs were disabled with no actions. The saved engine was Ollama `ministral-3:8b`, and that model was available. The fit queue contained 158 mixed-state records, not 158 active failures. No settings were changed.

Port 4819 refused a health connection. Kit Studio's MC app uses a per-instance port, so this does **not** establish that its actual MC instance was unavailable. Its current canvas instance and end-to-end integration were not tested.

Local audit artifacts are under `runs/maintainer-studio-catalog-review-20261020/`: pinned clones, file hashes, normalized records and keyword shortlist. Keyword matches include false positives and are not an approved stack. This report supplies a reuse direction; it does not claim installation or compatibility success.

## Alex catalog: acquisition shortlist after the scope clarification

The settled home is Link & Sync → Plugins: Market, organized installed plugins, Maintainer operations and Kit creation; separate Builder/Agent assignments; on-demand dynamic canvas access. Kit Studio is Maintainer's composition tool. The recommendation below means acquire/pin and qualify reusable components, not activate every overlapping manager.

### First group

1. **vlln/plugin-registry** — acquire its thin console, plugin development guidance and discovery/inspection pieces. Best fit for installed-state inspection and authoring contracts. Route mutations through Link & Sync. Pinned above.
2. **whyihaveyou/dsh-suite** — acquire the repository as a toolkit. Use the catalog/compatibility pipeline, `packages/create-dsh-plugin` and selected packages. Do not describe the suite root as a single plugin to install. The manager and registry console overlap; select their useful parts behind one MC experience.
3. **Noob-stupid/dsh-plugin-hub**, now **dsh-plugin-gating-hub** — prioritize its compatibility gates and update/readiness evidence for Maintainer. Source inspected at `84e663baa3ea416495bc5677902f3a6b4453ef12`: `lib/server/domain/contract-rules.js`, `install-finalize.js`; route/domain inventory inspected. MIT, package `@noob-stupid/dsh-plugin-console` 0.5.92. This review confirms code for rules and result mapping, not its advertised rollback guarantees. Framework-updater and auto-disable paths need explicit reconciliation with MC's lifecycle owner. Source: https://github.com/Noob-stupid/dsh-plugin-gating-hub
4. **leechen298/Code2Skill** — acquire for Studio's source-to-capability workflow. Produces Functions, MCP tools, Skills and offline validation packages from actual source invocation points. It is not a general plugin-source merger. README, package and pipeline source inspected at `afd25120129e4cfb69fb57d0c9dfea490e8a3c60`; `skills/code2skill-generate/scripts/run_pipeline.py` tracks validation/invalidation. MIT, 1.2.0; Node ^22.19 or >=24. Source: https://github.com/leechen298/Code2Skill
5. **FSMargoo/dsh-custom-tool** — acquire for small user/builder-authored tools and an editable code interface, potentially mounted on the canvas. README and `src/registry.ts` inspected at `7cb95649dca9b380c9a30af96bdbef87a76a2259`. Registrations, failures and workspace-scoped stores are explicit. Restricted workers are advertised; workspace path confinement is documented as lexical and symlink-sensitive. Worker isolation itself was not audited or tested. Source: https://github.com/FSMargoo/dsh-custom-tool

### Later, targeted qualification

- **william-jin-cmu/dsh-evolve** — whole Cordis plugin hot-mount/disposal and restart restoration; useful for experimental creation. `src/index.ts` imports generated modules and manages fibers; inspected at `37462647f89612ab89b18fadb88299e550748200`. BSD-3-Clause, 0.1.0; old ^0.0.1 DSH peer declarations. This is executable plugin loading, not merely editing a sandboxed function. Must use existing grants/lifecycle and first prove host compatibility. Source: https://github.com/william-jin-cmu/dsh-evolve
- **fakechris/dsh-harness-ops** — recovery and A/B rollout reference/toolkit, not an all-in-one MC replacement. README and `skills/dsh-snapshot-ab/scripts/ab.sh` inspected at `791d8ad59999103c7e6cfa56bb01dd822e4f5687`; switching/rollback restarts DSH web and uses its own slots. Evaluate specific recovery components against existing MC release/process ownership before adopting. Source: https://github.com/fakechris/dsh-harness-ops
- **suite/plugin-team-board** — useful create/claim/update/list tooling and a panel, but its own board.json would be another task authority if installed unchanged. README/package inspected; keep as a candidate for an adapter to existing tickets, not an automatic replacement. The currently declared DSH peers are ^0.1.0-rc.6.

### Canvas-facing follow-up leads

Alex also lists `dsh-artifact`, `dsh-genui`, `dsh-web-review`, `dsh-browser-panel` and `dsh-task-status`. These fit output descriptors, generated UI, visual review, browser operation and progress display respectively. These are catalog leads only in this review. Inventory existing MC installations before acquiring or adding them; DSH Web UI placement is not native MC canvas integration by itself.

No candidate code or test suite was executed. Final installed stack depends on artifact/host qualification. The recommended starting pool is Registry + selected Suite parts + Gating Hub checks + Code2Skill + Custom Tool, complemented by the Doctor/Test Drive/security tools from the broader review.
