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

## Published guidance checked 2026-10-20

Earlier component outlines were our proposed study format, not a checked external standard. The following primary-source review informs the next revision; existing captures and generated packs have not been migrated or certified conformant.

- [Google Labs DESIGN.md format](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md): an alpha format joining design prose with structured YAML tokens. Its core section sequence is Overview, Colors, Typography, Layout, Elevation & Depth, Shapes, Components, and Do's and Don'ts. Supported token references connect semantic roles to values. Do not fabricate values to fill the format; preserve uncertainty in the study evidence.
- [Google Labs DESIGN.md philosophy](https://github.com/google-labs-code/design.md/blob/main/PHILOSOPHY.md): articulate intent and specific design references, explain where tokens apply, and give deliberate constraints. A detailed value inventory does not substitute for a coherent design direction.
- [Stitch design-md extraction guidance](https://github.com/google-labs-code/stitch-skills/blob/main/plugins/stitch-utilities/skills/design-md/SKILL.md): combine visual assets and HTML/style information, then describe atmosphere, functional color roles, typography, component treatment and spatial principles. This is a related workflow, not an identical version of the alpha format.
- [Figma MCP best practices](https://help.figma.com/hc/en-us/articles/34855090823063-MCP-server-best-practices): supply structured design context and its screenshot, meaningful names, variables, annotations and mappings to actual components. Work on bounded selections, adapt to existing repository conventions, then validate appearance and behavior. Figma-specific capabilities are guidance, not claims that our website collector recovers native Figma structure.
- [OpenAI vision limitations](https://developers.openai.com/api/docs/guides/images-vision#limitations): small text, resizing and precise spatial reasoning limit image-only measurements. Supplement pictures with actual structure/style evidence when available.

### Application to our packs — proposed revision

Keep the human presentation and agent guide linked, while giving them distinct jobs:

1. **Visual reference:** full screen/flow, named annotated parts, palette/type previews and observed states.
2. **DESIGN.md:** a concise semantic design guide using the eight core sections above. Describe hierarchy, role-specific styling, intended feel, usage rules and constraints. Include measured tokens where available and explicit omissions where needed.
3. **Component/evidence sidecars:** selectors, anatomy, dimensions, variants, inputs/events, source/version, observation basis, assets/rights, uncertain values and runtime evidence. Link these by stable IDs; keep raw extraction logs out of the main design narrative.
4. **Build brief:** select relevant references by purpose. State what to borrow/adapt, the target task/framework, existing component/token mappings and accepted differences. When combining references, produce one coherent target direction rather than leave conflicting styles unresolved.
5. **Agent context:** start with the relevant guide, full-screen context and selected component views. Retrieve deeper sidecars as needed; do not inject the entire catalog or assume an image path means a vision model viewed it.
6. **Validation:** build a bounded real screen with existing tools, compare it to the intended direction, exercise responsive/interaction states and retain corrections. Test a pack-only handoff separately; our first builder had also seen screenshots, so that was not a blind test.

This is our application of the guidance, not a published universal website-reconstruction standard. REA supplies evidence; design interpretation, target-code mapping and build evaluation remain necessary. Next: revise the two pilot packs before resuming semantic automation or scale-up. Preserve the approved overall library design.
