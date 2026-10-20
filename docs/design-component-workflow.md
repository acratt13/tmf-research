# Visual design studies and agent handoff

Andy’s direction: show people the full design and its parts; let DESIGN.md pull the same evidence together for an agent. Preserve source categories and the existing MC catalog owner.

## One study, two presentations

The human view opens with the real screen or recorded interaction. Beneath it, show annotated component cards, palette swatches, typography, layout relationships, responsive variants and observed states. Each part links to its position in the whole screen and explains its role in plain language. Raw DOM candidates stay out of the curated view.

DESIGN.md follows the visual breakdown and can be downloaded. It consolidates the same component identities, tokens, structure, behaviors, dependencies, responsive rules and evidence into an agent-readable build brief. Structured JSON preserves those identities and exact evidence references for retrieval. These are presentations of one study, not separately maintained catalogs.

## Collection and analysis

1. Discover the original site from its source category. Preserve discovery URL, original URL and capture date.
2. Crawlee captures bounded public screens and measurements. REA examines structure and controlled interactions where the ordinary capture is insufficient. Record which tool produced each fact.
3. Review the actual pictures and interaction result. A completed capture does not establish a ready or populated interface.
4. Divide the screen into meaningful parts: shell, layout, content components, controls, scene layers and persistent overlays. Keep composition and parent/child relationships.
5. Attach visual evidence, explanation, tokens and observed states to each part. Distinguish stylesheet declarations, computed styles, runtime observations and analyst proposals.
6. Generate the human presentation, DESIGN.md and component JSON from the linked study. Original scene code or editable authoring files may remain unavailable.

## DESIGN.md contents

- Source, category, date, provenance and tested viewports.
- Overall composition and intended visual effect.
- Palette and typography with exact values only where evidence supports them.
- Component map using the same IDs as the human view.
- Component anatomy, hierarchy, spacing, styles, data and state transitions.
- Motion triggers and verified behavior; unknown timings remain unknown.
- Responsive and accessibility observations, with untested cases explicit.
- Implementation evidence and dependencies, separate from proposed architecture.
- Agent reconstruction guidance and clear acceptance checks.
- Linked screenshots, source records and evidence hashes.

## Optional implementation output

When the task requires a reusable implementation, add component source, scoped styles/tokens, an input/event contract, dependencies and a live usage example. Label it recovered source only when actual source and reuse rights establish that; otherwise label it an independent reconstruction. Reference studies remain useful without claiming to contain usable production code.

Keep card content separate from scene positioning, camera, shader and interaction-controller ownership. A screenshot crop is visual evidence; it is not an extracted 3D mesh or recovered React module.

## Current proof and limits

Local NK study: runs/design-crawl-20261020/rea-nk. Actual local REA CLI from repository commit c12d9eda87aa5a022ee7e18ea96d8d03bfd12e96 captured intro and populated archive states. The first insufficiently settled archive was retained. Stylesheets independently establish color and font declarations. Seven analytical visual parts and DESIGN.md/JSON were generated.

An optional independent story-card Web Component demonstrates a portable input/event/style boundary. Mouse activation, keyboard Enter, host selection and Tab skipping disabled state were exercised in the browser. This does not prove the original gallery’s scene, card opening, dragging, mobile behavior or reduced-motion runtime.

The generic Crawlee gallery now supports search, top categories, a screenshot grid and an opened study with selected components and DESIGN.md below. Automatic REA orchestration, scene reconstruction and automatic synthesis of this richer semantic format are not yet implemented. No bulk MC ingestion or publication has occurred.
