# WordCraft / GridCraft / DeckCraft trial

2026-10-19 · All three actual v0.8.0 command-line engines ran locally on macOS. This is a bounded headless-engine trial, not proof of native GUI interaction or an integrated research-agent application.

## Results

| Application | Actual actions and readback | Outputs |
| --- | --- | --- |
| WordCraft | Converted original Markdown to DOCX; reopened it, appended review status, saved; read the text back; inspected DOCX XML independently; exported PDF and rendered page 1 | [DOCX](../examples/craft-trial/briefing.docx), [PDF](../examples/craft-trial/briefing.pdf), [preview](../examples/craft-trial/report-preview.png) |
| GridCraft | Created a formatted six-service XLSX table; reopened and edited it; verified three formula values (6, 6, 0); engine roundtrip check reported no mismatches/differences; exported CSV/HTML and independently read CSV | [XLSX](../examples/craft-trial/service-readiness.xlsx), [CSV](../examples/craft-trial/service-readiness.csv) |
| DeckCraft | Created six original slides; reopened PPTX and edited final-slide notes; independently read slide/notes XML; exported PDF/Markdown and rendered all six PNGs | [PPTX](../examples/craft-trial/briefing.pptx), [PDF](../examples/craft-trial/slides.pdf), [outline](../examples/craft-trial/slides.md), [preview](../examples/craft-trial/presentation-preview.png) |

The source is our proposed professional-services specification at the exact linked repository revision. Six selected service families are still marked Specified, not Client accepted. No private customer or prospect data is included. The pack is a presentation/adapter pilot, not a completed client implementation or independent demand study.

Official release archives matched their published SHA256 files. macOS verified all three CLI signatures under Learning Machines LLC, team identifier DJ6XS33FX8. Tools are privately staged outside the published source; no system-wide app installation was performed. [Machine-readable receipt and output hashes](../examples/craft-trial/verification.json).

## Reproduce

Obtain each upstream v0.8.0 CLI from its official release and verify it under your own environment's policies. Then:

```bash
python scripts/try_craft.py \
  --wordcraft /path/to/wordcraft-cli \
  --gridcraft /path/to/gridcraft-cli \
  --deckcraft /path/to/deckcraft-cli \
  --output runs/craft-trial-new
```

The script requires a new output directory, retains each command's stdout/stderr, and reports per-application results. It does not install software or call a model, search service or network API.

## Limits and findings

- Initial DeckCraft PNG invocation used an unsupported `--in` flag. It failed with exit 1; the script was corrected to the actual positional-file contract. Failed first-run logs remain local; the final full run passed.
- WordCraft's first page and DeckCraft slides 1 and 6 were visually inspected. All generated PDFs were text-read for critical content and source references. This is not a full cross-platform typography review.
- GridCraft HTML export retained data but not the XLSX table styling; its plain table can require horizontal scrolling. Do not treat it as a premium workbook preview.
- GridCraft's calc oracle and roundtrip check used a file created by GridCraft. Explicit values were also checked, but actual Excel interoperability, other producers' formula caches, and complex legacy files remain untested.
- At this trial: native GUI editing, MCP agent sessions, embedded shared revisions and runtime research-workbench adapters were untested or unimplemented. The subsequent local CLI research adapters are documented in [WORKBENCH.md](WORKBENCH.md); native editing/Microsoft interoperability remain unverified.
- PDF/native files are useful outputs; production suitability, complete Microsoft fidelity and all advertised upstream features have not been established.

No upstream binaries, source, icons or branding assets are redistributed. The original generated study and script are part of this repository; upstream code, fonts and other assets retain their own terms.
