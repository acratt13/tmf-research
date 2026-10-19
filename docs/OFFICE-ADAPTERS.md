# Open-source Office alternatives for research outputs

Researched 2026-10-19. Documentation comparison only; no editor integration or installation performed. These are alternatives to Microsoft applications, not Microsoft source code. Recommendations below are design judgments, not benchmark results or legal clearance.

| Candidate | Useful role in TMF Research | Documented boundary / tradeoff |
| --- | --- | --- |
| LibreOffice | First candidate for free document/spreadsheet/presentation editing and automated conversion | Writer, Calc and Impress cover the core suite. Official conversion filters expose command-line export including PDF and Microsoft formats. Fidelity, font packaging and our actual roundtrip must be tested. [Suite](https://www.libreoffice.org/), [Conversion filters](https://help.libreoffice.org/latest/en-US/text/shared/guide/convertfilters.html), [Licenses](https://www.libreoffice.org/licenses/) |
| Univer | First candidate for an editable spreadsheet/document surface embedded in our own UI | Open-source core is Apache-2.0 and includes spreadsheet/document/presentation foundations. Upstream lists important import/export, printing and collaboration features under its commercial Pro extensions. Do not describe the entire suite as freely embeddable with all advanced features included. [Repository and OSS/Pro matrix](https://github.com/dream-num/univer) |
| ONLYOFFICE Docs Community | Evaluate for ready-made browser-based office editors | Vendor documents AGPLv3, attribution/branding conditions and separate commercial licensing. Confirm the exact integration and distribution model before selecting it; retain vendor notices. Community support is not a guaranteed SLA. [Official licensing FAQ](https://helpcenter.onlyoffice.com/docs/faq/docs-community.aspx) |
| Collabora Online / CODE | Evaluate for collaborative browser editing around an office document server | Free CODE is the development edition; vendor does not recommend it for production. Supported Collabora Online is a separate subscription offering. [Integration and edition comparison](https://www.collaboraonline.com/integrate-collabora-online/) |

## Proposed selection

For the first free export/conversion path, investigate **LibreOffice**. For an embedded, programmable Office-like editing surface, evaluate **Univer's exact OSS packages**. Keep ONLYOFFICE and Collabora as alternatives when their architecture and licensing/support model fit the client deployment.

This choice does not replace Archify: diagrams remain their own renderer, with editable diagram specifications and exported artifacts linked to the research revision. Office documents, slides and spreadsheets are additional views of the same evidence and requirements.

## Required proof before adopting an adapter

1. Identify exact edition, repository revision/packages, license and included features.
2. Open an original sample with citations, requirements, table, diagram and explicit unknowns.
3. Edit, save, close and reopen it; verify the changed revision and original evidence references.
4. Export the promised file formats and inspect the resulting layout and content.
5. Verify missing fonts, unsupported formats, errors and unavailable conversions remain visible.
6. Re-import where promised and compare semantics; never promise perfect Microsoft fidelity from a feature list.
7. Verify isolation, temporary-file cleanup, provider dependencies, resource use and redistribution obligations for the target deployment.

No candidate is currently wired into the TMF Research runtime. The existing Markdown/HTML/PDF core and separately generated Archify design are the implemented outputs.
