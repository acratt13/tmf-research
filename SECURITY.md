# Security and privacy

This early release is a local CLI for operator-selected records and artifacts. It is not a hosted multi-tenant service, sandbox or permission boundary. Do not expose its commands directly to untrusted remote users.

`inspect` launches an explicitly supplied local REA command without a shell. REA and its parsers still process untrusted artifacts; isolation/resource controls are the operator's responsibility. The timeout bounds the directly launched process; descendant cleanup, total CPU/memory and process output generation are not fully bounded by this wrapper. The 16 MiB output check is a retained-output limit after capture, not a streaming allocation cap. Use small selected targets and inspect REA's original limits.

Reports and raw REA envelopes may contain sensitive paths, URLs, strings or metadata. The tool does not automatically sanitize every secret or private datum. Keep private runs outside shared/published directories. Review artifacts before distribution. No network/model provider is contacted by the evidence/report core; explicitly invoking external REA can involve its own behavior and dependencies.

HTML report text is escaped, with no scripts or remote resources. Markdown escapes input markup. These measures do not make arbitrary inputs trustworthy or replace renderer/editor-specific security reviews. PDF export uses an optional dependency and should run in the same isolated environment used for untrusted documents.

To report a vulnerability, use GitHub private vulnerability reporting if enabled. Otherwise open an issue requesting a private contact without including exploit payloads, credentials or client data. Do not publish confidential details in an issue.
