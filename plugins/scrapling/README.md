# Scrapling collection plugin

Research's second crawler (Owner 2026-11-06: "add them both as plugins"; "we make the research machine just run on
plugins"). The shared Crawlee worker does steady bulk collection; this plugin collects the sites it could not (bot blocks,
changed layouts), with [Scrapling](https://github.com/D4Vinci/Scrapling) (BSD-3-Clause): its plain fetcher first, its
StealthyFetcher (a real browser fingerprint) when that is refused.

Boundaries, the same as Crawlee: public HTTPS on 443 only (DNS checked, redirects re-checked); robots.txt is required and
honoured, and an unreadable policy fails closed; Cloudflare challenge-solving is OFF. Fetched text is untrusted reference
data: no analysis, outreach or KB ingestion here.

It is a minimal MCP server over stdio (`server.py`), run as
`uv run --no-project --with "scrapling[fetchers]==0.5.1" python server.py` (dependencies in uv's cache; nothing installed
on the host). Tools: `scrapling_status`, `scrapling_fetch {url, stealth?}` -> `{final_url, text, text_sha256, fetcher, ...}`.
`tmf-plugin.json` imports it into MC like the Crawlee plugin. Research's pre-build swarm calls it through
`tmf_research.providers.ScraplingPlugin`; override the command with `{"crawlers": {"scrapling": {"command": [...]}}}`.
StealthyFetcher needs a Playwright Chromium on the host (`scrapling install`).
