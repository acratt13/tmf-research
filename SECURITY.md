# Security and privacy

This early release is a local CLI and loopback workbench for operator-selected research and artifacts. It is not a hosted multi-tenant service or a security sandbox. Do not expose it to untrusted remote users.

`inspect` and the research REA adapter launch explicitly configured commands without a shell. A shared process wrapper streams and bounds combined stdout/stderr, applies a wall timeout and kills/reaps the POSIX child process group on violation. Windows cleanup covers the direct process. This is not a CPU/memory sandbox: REA and external renderers process untrusted input, and their own isolation/resource controls still matter. Select small targets and read REA's coverage/limits.

Reports, snapshots and raw REA envelopes may contain sensitive paths, URLs, strings or metadata. Local files are not encrypted by this project. Redaction is incomplete; select only material intended for model transfer, keep private runs outside shared/published directories, and review artifacts before distribution. `validate`, `render` and `import-rea` do not contact a provider. `run`/`serve` research explicitly sends the brief, retrieved public excerpts and selected local REA excerpts to the Codex model provider, using existing authentication without copying credential files.

The model adapter pins the tested CLI 0.160.1 capability boundary, ignores user configuration/rules, suppresses skills/plugins/hooks and execution tools, and uses fresh ephemeral role contexts. Native web search is enabled only for the scout and must produce a recorded search event. These measures limit tools; they do not establish model reliability or provider diversity. Retrieval content remains untrusted data. A quote match and a second model's agreement are not factual certification.

Public HTTPS retrieval validates and pins global destination addresses, verifies hostname TLS, rechecks redirects, does not inherit environment proxies/cookies, and bounds body bytes and socket wall time. OS DNS uses the resolver's own timeout. The server binds to 127.0.0.1 with Host/Origin and request-token checks; it has no hosted tenant/session isolation. Cancellation and interrupted states retain evidence rather than declaring success or automatically replaying work.

HTML report text is escaped, with no scripts or remote resources. Markdown escapes input markup. These measures do not make arbitrary inputs trustworthy or replace renderer/editor-specific security reviews. PDF export uses an optional dependency and should run in the same isolated environment used for untrusted documents.

To report a vulnerability, use GitHub private vulnerability reporting if enabled. Otherwise open an issue requesting a private contact without including exploit payloads, credentials or client data. Do not publish confidential details in an issue.
