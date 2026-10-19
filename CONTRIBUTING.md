# Contributing

Start with the current capability table in README and the research-workbench specification. Keep claims about implemented behavior separate from design proposals.

Use Python 3.11+ and run `python -m unittest discover -s tests -v`. The core intentionally has no third-party runtime dependencies; discuss new dependencies before adding them. Test failure/partial/unknown outcomes, citation preservation and output ownership when touching evidence or export code.

Use original synthetic fixtures or redistribution-safe public examples. Do not submit private email, client/prospect data, credentials, proprietary binaries, or confidential reports. Do not commit run outputs by default.

For research adapters, document provider access, cost controls, failure states, privacy boundaries and evidence provenance. For presentation adapters, demonstrate open/edit/save/reopen/export and preservation of citations/caveats. A screenshot or menu entry alone does not establish integration.

For significant changes, open an issue describing the user problem, bounded change, acceptance evidence and limitations. Small focused pull requests are welcome. Preserve upstream attribution and licenses.
